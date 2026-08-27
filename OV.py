# OV.py
#
# Copyright 2010 AL Haines (from original MyFunctions.php)
#
# This module provides a Pythonic class and functions for generating HTML
# output, translating the functionality found in the original PHP MyFunctions.php.
# It includes methods for basic HTML tags, table generation, and specific
# functions for OverLib (onmouseover) integration.

import re
import subprocess
import socket
import sys
from datetime import datetime

try:
    from rich.console import Console
    from rich.table import Table
except ImportError:  # pragma: no cover
    Console = None
    Table = None


def get_disk_usage_data():
    """Run 'df -T' and return parsed rows."""
    command = ['df', '-T', '-x', 'tmpfs', '-x', 'devtmpfs', '-x', 'squashfs']
    try:
        result = subprocess.run(command, capture_output=True, text=True, check=False)
        if not result.stdout.strip():
            print(f"Error: 'df' command produced no output. stderr: {result.stderr}", file=sys.stderr)
            return None

        lines = result.stdout.strip().split('\n')
        data_lines = lines[1:]

        parsed_data = []
        for line in data_lines:
            parts = re.split(r'\s+', line)
            if len(parts) < 7:
                continue

            try:
                total_kb = int(parts[2])
                used_kb = int(parts[3])
                free_kb = int(parts[4])
            except ValueError:
                continue

            parsed_data.append(
                {
                    'device': parts[0],
                    'type': parts[1],
                    'mountpoint': parts[6],
                    'total_kb': total_kb,
                    'used_kb': used_kb,
                    'free_kb': free_kb,
                }
            )

        return parsed_data

    except (subprocess.CalledProcessError, FileNotFoundError) as e:
        print(f"Error executing 'df' command: {e}", file=sys.stderr)
        return None


def get_mount_access_mode(mountpoint):
    """Read /proc/mounts and return mount mode as 'rw', 'ro', or 'unknown'."""
    try:
        with open('/proc/mounts', 'r', encoding='utf-8') as mounts_file:
            for line in mounts_file:
                parts = line.split()
                if len(parts) < 4:
                    continue

                current_mount = parts[1].replace('\\040', ' ')
                if current_mount != mountpoint:
                    continue

                options = parts[3].split(',')
                if 'ro' in options:
                    return 'ro'
                if 'rw' in options:
                    return 'rw'
                return 'unknown'
    except OSError:
        return 'unknown'

    return 'unknown'


def classify_entry(entry):
    """Classify entry into Internal Drives, External Drives, or Mounted Shares."""
    device = entry.get('device', '')
    fstype = entry.get('type', '').lower()
    mount = entry.get('mountpoint', '')

    if device.startswith('//') or (':' in device and not device.startswith('/dev')):
        return 'Mounted Shares'
    if fstype in ('nfs', 'nfs4', 'cifs', 'smbfs', 'smb', 'sshfs', 'fuse.sshfs'):
        return 'Mounted Shares'

    if mount.startswith('/media') or mount.startswith('/run/media') or mount.startswith('/mnt'):
        return 'External Drives'

    if re.match(r'^/dev/(sd|hd|nvme|mmcblk|mapper|vd)', device):
        return 'Internal Drives'

    return 'Internal Drives'


def get_entry_endpoint(entry):
    """Return source shown in table (device for local, endpoint for shares)."""
    return entry.get('device', '-')


def get_share_status(entry):
    """Return share status: local/reachable/timeout/stale-unreachable/unreachable/unknown."""
    if classify_entry(entry) != 'Mounted Shares':
        return 'local'

    mountpoint = entry.get('mountpoint', '')
    if not mountpoint:
        return 'unknown'

    try:
        result = subprocess.run(
            ['timeout', '2', 'stat', '-f', mountpoint],
            capture_output=True,
            text=True,
            check=False,
        )
        if result.returncode == 0:
            return 'reachable'
        if result.returncode == 124:
            return 'timeout'

        error_text = f"{result.stdout}\n{result.stderr}".lower()
        stale_markers = (
            'stale file handle',
            'transport endpoint is not connected',
            'no route to host',
            'connection timed out',
            'input/output error',
        )
        if any(marker in error_text for marker in stale_markers):
            return 'stale/unreachable'
        return 'unreachable'

    except FileNotFoundError:
        try:
            result = subprocess.run(
                ['stat', '-f', mountpoint],
                capture_output=True,
                text=True,
                check=False,
                timeout=2,
            )
            return 'reachable' if result.returncode == 0 else 'unreachable'
        except subprocess.TimeoutExpired:
            return 'timeout'
        except Exception:
            return 'unknown'
    except Exception:
        return 'unknown'


def format_state_code(status):
    """Map status to compact state letters: l=local, r=reachable, s=problem."""
    if status == 'local':
        return '[dim]l[/dim]'
    if status == 'reachable':
        return '[green]r[/green]'
    return '[bold red]s[/bold red]'


def format_gb_short(size_gb):
    return f"{size_gb:.1f}G"


def format_free_value(free_gb, free_pct):
    """Color free-space text by free percentage."""
    value_text = format_gb_short(free_gb)
    if free_pct < 5:
        return f"[bold red]{value_text}[/bold red]"
    if free_pct <= 20:
        return f"[yellow]{value_text}[/yellow]"
    if free_pct >= 80:
        return f"[green]{value_text}[/green]"
    return f"[cyan]{value_text}[/cyan]"


def get_health_status(percent_used):
    if percent_used > 90:
        return '[bold red]CRIT[/bold red]'
    if percent_used > 70:
        return '[yellow]WARN[/yellow]'
    return '[green]OK[/green]'


def build_extended_table(groups, machine_name, checked_at):
    """Build optional extended table (inode column removed)."""
    if Table is None:
        raise RuntimeError("rich is required for build_extended_table()")

    ext_table = Table(title=f"Extended Disk Info ({checked_at})", show_footer=False)
    ext_table.add_column(machine_name, style='cyan', no_wrap=True)
    ext_table.add_column('Drive', style='cyan', overflow='fold', max_width=24)
    ext_table.add_column('Mountpoint', style='magenta', overflow='fold', max_width=28)
    ext_table.add_column('FS Type', justify='center')
    ext_table.add_column('Free %', justify='right')
    ext_table.add_column('Health', justify='center')

    for grp_name in ('Internal Drives', 'External Drives', 'Mounted Shares'):
        items = groups.get(grp_name, [])
        if not items:
            continue

        ext_table.add_row(f"[bold magenta]{grp_name}[/bold magenta]", '', '', '', '', '')

        items_sorted = sorted(items, key=lambda x: x['free_kb'], reverse=True)
        for item in items_sorted:
            ext_table.add_row(
                item['hostname'],
                item['device'],
                item['mountpoint'],
                item['type'],
                f"{item['free_pct']:.1f}%",
                item['health_status'],
            )

        ext_table.add_row('', '', '', '', '', '', end_section=True)

    return ext_table


class OV:
    """
    A class to encapsulate HTML output functions, mimicking the PHP OV class.
    Methods directly print HTML strings to standard output, similar to PHP's echo.
    """

    def encrypt_it(q):
        """
        Translates the PHP encryptIt function using Python's cryptography library
        for similar (but more secure and modern) encryption.
        NOTE: The original PHP function used `mcrypt_encrypt` which is deprecated.
        This implementation uses AES in CBC mode with a randomly generated IV
        (Initialization Vector) for each encryption, which is standard practice
        and more secure. The PHP version used MD5 of MD5 for IV, which is not ideal.
        This function will require `pip install cryptography`.

        Args:
            q (str): The string to encrypt.

        Returns:
            str: The base64 encoded encrypted string.
        """
        from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes
        from cryptography.hazmat.backends import default_backend
        from cryptography.hazmat.primitives import hashes, kdf
        import base64
        import os # For os.urandom

        # This key is derived from the PHP function's hardcoded 'qJB0rGtIn5UB1xG03efyCp'
        # For actual production, DO NOT hardcode keys like this.
        # Generate a strong, random key and manage it securely.
        crypt_key_material = 'qJB0rGtIn5UB1xG03efyCp'.encode('utf-8')
        key_hash = hashes.Hash(hashes.MD5(), backend=default_backend())
        key_hash.update(crypt_key_material)
        key = key_hash.finalize() # This is the MD5 hash of the key material, 16 bytes

        # Generate a random IV for each encryption (16 bytes for AES block size)
        iv = os.urandom(16)

        # Pad the data to be a multiple of the block size
        # PKCS7 padding is standard.
        padder = algorithms.AES.block_size // 8
        q_bytes = q.encode('utf-8')
        padding_len = padder - (len(q_bytes) % padder)
        padded_q = q_bytes + bytes([padding_len]) * padding_len

        cipher = Cipher(algorithms.AES(key), modes.CBC(iv), backend=default_backend())
        encryptor = cipher.encryptor()
        ct = encryptor.update(padded_q) + encryptor.finalize()

        # Base64 encode the IV and ciphertext. The IV is crucial for decryption.
        # We combine IV and ciphertext for easier transfer.
        return base64.b64encode(iv + ct).decode('utf-8')


    def decrypt_it(q_encoded):
        """
        Translates the PHP decryptIt function using Python's cryptography library.
        NOTE: This expects the output format of `encrypt_it` (IV + ciphertext, base64 encoded).

        Args:
            q_encoded (str): The base64 encoded encrypted string (containing IV + ciphertext).

        Returns:
            str: The decrypted string.
        """
        from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes
        from cryptography.hazmat.backends import default_backend
        from cryptography.hazmat.primitives import hashes
        import base64

        # This key is derived from the PHP function's hardcoded 'qJB0rGtIn5UB1xG03efyCp'
        # For actual production, DO NOT hardcode keys like this.
        crypt_key_material = 'qJB0rGtIn5UB1xG03efyCp'.encode('utf-8')
        key_hash = hashes.Hash(hashes.MD5(), backend=default_backend())
        key_hash.update(crypt_key_material)
        key = key_hash.finalize() # This is the MD5 hash of the key material, 16 bytes

        decoded_data = base64.b64decode(q_encoded)

        # Extract the IV (first 16 bytes for AES block size)
        iv = decoded_data[:16]
        ct = decoded_data[16:]

        cipher = Cipher(algorithms.AES(key), modes.CBC(iv), backend=default_backend())
        decryptor = cipher.decryptor()
        padded_plaintext = decryptor.update(ct) + decryptor.finalize()

        # Remove PKCS7 padding
        padding_len = padded_plaintext[-1]
        plaintext = padded_plaintext[:-padding_len]

        return plaintext.decode('utf-8')

    def E(self, text):
        """
        The simple way to print text directly.
        Corresponds to PHP's OV::E($text).
        """
        print(text)

    def Image(self, url, width=-1, height=-1, border=-1, title=-1, map_name=-1, name=-1, class_name=-1):
        """
        Generates an HTML <img> tag.
        Corresponds to PHP's OV::Image().

        Args:
            url (str): The source URL of the image.
            width (int, optional): The width of the image. Defaults to -1 (not set).
            height (int, optional): The height of the image. Defaults to -1 (not set).
            border (int, optional): The border width of the image. Defaults to -1 (not set).
            title (str, optional): The title attribute for the image (tooltip). Defaults to -1 (not set).
            map_name (str, optional): The USEMAP attribute value (without the #). Defaults to -1 (not set).
            name (str, optional): The name attribute for the image. Defaults to -1 (not set).
            class_name (str, optional): The class attribute for the image. Defaults to -1 (not set).
        """
        options = []
        if width != -1:
            options.append(f'WIDTH="{width}"')
        if height != -1:
            options.append(f'HEIGHT="{height}"')
        if border != -1:
            options.append(f'BORDER="{border}"')
        if title != -1:
            options.append(f'TITLE="{title}"')
        if map_name != -1:
            # Corrected f-string syntax: directly embed the variable map_name
            options.append(f'USEMAP="#{map_name}"') # Note: PHP used #$map
        if name != -1:
            options.append(f'NAME="{name}"')
        if class_name != -1:
            options.append(f'CLASS="{class_name}"')

        options_str = " ".join(options)
        print(f'<IMG SRC="{url}" {options_str}>')

    def AStart(self, url, action=-1, class_name=-1):
        """
        Generates the opening <A HREF> tag.
        Corresponds to PHP's OV::AStart().

        Args:
            url (str): The URL for the hyperlink.
            action (str, optional): Additional attributes for the tag (e.g., onmouseover, onclick). Defaults to -1 (not set).
            class_name (str, optional): The class attribute for the link. Defaults to -1 (not set).
        """
        option_class = ""
        if class_name != -1:
            option_class = f' CLASS="{class_name}"'

        if action != -1:
            print(f'<A HREF="{url}" {action}{option_class}>')
        else:
            print(f'<A HREF="{url}"{option_class}>')

    def AEnd(self):
        """
        Generates the closing </A> tag.
        Corresponds to PHP's OV::AEnd().
        """
        print('</A>')

    def Bold(self, text, class_name=-1):
        """
        Puts the text in bold using <B> tag.
        Corresponds to PHP's OV::Bold().

        Args:
            text (str): The text content.
            class_name (str, optional): The class attribute for the tag. Defaults to -1 (not set).
        """
        option_class = ""
        if class_name != -1:
            option_class = f' CLASS="{class_name}"'
        print(f'<B {option_class}>{text}</B>')

    def Br(self, nbr=-1):
        """
        Generates one or more <BR> tags for line breaks.
        Corresponds to PHP's OV::Br().

        Args:
            nbr (int, optional): The number of <BR> tags to generate. Defaults to -1 (one <BR>).
        """
        if nbr != -1:
            for _ in range(nbr):
                print('<BR>')
        else:
            print('<BR>')

    def DivEnd(self):
        """
        Generates the closing </DIV> tag.
        Corresponds to PHP's OV::DivEnd().
        """
        print('</DIV>')

    def Head(self):
        """
        Generates the opening <!DOCTYPE html><html><head> tags.
        Corresponds to PHP's OV::Head().
        """
        print('<!DOCTYPE html><html><Head>')

    def HeadEnd(self):
        """
        Generates the closing </Head> tag.
        Corresponds to PHP's OV::HeadEnd().
        """
        print('</Head>')

    def Div(self, id_name=-1, style=-1, align=-1):
        """
        Generates an opening <DIV> tag with optional attributes.
        Corresponds to PHP's OV::Div().

        Args:
            id_name (str, optional): The id attribute for the div. Defaults to -1 (not set).
            style (str, optional): The style attribute for the div. Defaults to -1 (not set).
            align (str, optional): The align attribute for the div. Defaults to -1 (not set).
        """
        options = []
        if id_name != -1:
            options.append(f'id="{id_name}"')
        if style != -1:
            options.append(f'style="{style}"')
        if align != -1:
            options.append(f'ALIGN="{align}"')

        options_str = " ".join(options)
        print(f'<DIV {options_str}>')

    def Style(self, url):
        """
        Generates a <LINK> tag for including an external stylesheet.
        Corresponds to PHP's OV::Style().

        Args:
            url (str): The URL of the stylesheet.
        """
        print(f'<link href="{url}" rel="stylesheet" type="text/css">')

    def Refresh(self, href, delay=-1):
        """
        Generates a <meta http-equiv=REFRESH> tag for page refresh/redirect.
        Corresponds to PHP's OV::Refresh().

        Args:
            href (str): The URL to refresh to.
            delay (int, optional): The refresh delay in seconds. Defaults to -1 (not set).
        """
        options = ""
        if delay != -1:
            options = str(delay)
        print(f"<meta http-equiv=REFRESH content='{options}; URL=\"{href}\"' >")

    def Body(self, action=-1):
        """
        Generates the opening <BODY> tag with optional attributes.
        Corresponds to PHP's OV::Body().

        Args:
            action (str, optional): Additional attributes for the body (e.g., onload). Defaults to -1 (not set).
        """
        if action != -1:
            print(f'<BODY {action}>')
        else:
            print('<BODY>')

    def BodyEnd(self):
        """
        Generates the closing </BODY> tag.
        Corresponds to PHP's OV::BodyEnd().
        """
        print('</BODY>')

    def TblStart(self, border="1", width=-1, height=-1, cell_spacing="2",
                 cell_padding="4", border_color=-1, class_name=-1, align=-1, back_color=-1):
        """
        Generates the opening <TABLE> tag with various attributes.
        Corresponds to PHP's OV::TblStart().

        Args:
            border (str, optional): The border width. Defaults to "1".
            width (int, optional): The width of the table. Defaults to -1 (not set).
            height (int, optional): The height of the table. Defaults to -1 (not set).
            cell_spacing (str, optional): Space between cells. Defaults to "2".
            cell_padding (str, optional): Padding within cells. Defaults to "4".
            border_color (str, optional): Color of the table border. Defaults to -1 (not set).
            class_name (str, optional): Class attribute for the table. Defaults to -1 (not set).
            align (str, optional): Alignment of the table. Defaults to -1 (not set).
            back_color (str, optional): Background color of the table. Defaults to -1 (not set).
        """
        options = []
        options.append(f'BORDER="{border}"')
        options.append(f'CELLSPACING="{cell_spacing}"')
        options.append(f'CELLPADDING="{cell_padding}"')

        if border_color != -1:
            options.append(f'BORDERCOLOR="{border_color}"')
        if class_name != -1:
            options.append(f'CLASS="{class_name}"')
        if width != -1:
            options.append(f'WIDTH="{width}"')
        if height != -1:
            options.append(f'HEIGHT="{height}"')
        if align != -1:
            options.append(f'ALIGN="{align}"')
        if back_color != -1: # PHP's `backcolor` parameter was not used in the `echo` line for TblStart
             # Based on original PHP, this param was present but not applied in the output.
             # If it was intended for BGCOLOR, it would be added here.
             pass

        options_str = " ".join(options)
        print(f'<TABLE {options_str}>')

    def TblEnd(self):
        """
        Generates the closing </TABLE> tag.
        Corresponds to PHP's OV::TblEnd().
        """
        print('</TABLE>')

    def TblStartLine(self, align=-1, bg=-1, action=-1, class_name=-1):
        """
        Generates the opening <TR> (table row) tag with optional attributes.
        Corresponds to PHP's OV::TblStartLine().

        Args:
            align (str, optional): Vertical or horizontal alignment ("top", "bottom", "left", "right", "center"). Defaults to -1 (not set).
            bg (str, optional): Background color or image URL. Defaults to -1 (not set).
            action (str, optional): Additional attributes (e.g., onclick). Defaults to -1 (not set).
            class_name (str, optional): Class attribute for the row. Defaults to -1 (not set).
        """
        options = []
        if align != -1:
            if align in ["bottom", "top"]:
                options.append(f'VALIGN="{align}"')
            elif align in ["left", "right", "center"]:
                options.append(f'ALIGN="{align}"')

        if bg != -1:
            if bg.startswith("#"):
                options.append(f'BGCOLOR="{bg}"')
            else:
                options.append(f'BACKGROUND="{bg}"')

        if class_name != -1:
            options.append(f'CLASS="{class_name}"')

        options_str = " ".join(options)
        if action != -1:
            print(f'<TR {options_str} {action}>')
        else:
            print(f'<TR {options_str}>')

    def TblEndLine(self):
        """
        Generates the closing </TR> tag.
        Corresponds to PHP's OV::TblEndLine().
        """
        print('</TR>')

    def TblEntete(self, content, bg=-1, nb_lig=1, nb_col=1):
        """
        Generates a <TH> (table header) tag.
        Corresponds to PHP's OV::TblEntete().

        Args:
            content (str): The content of the header cell.
            bg (str, optional): Background color. Defaults to -1 (not set).
            nb_lig (int, optional): ROWSPAN attribute. Defaults to 1.
            nb_col (int, optional): COLSPAN attribute. Defaults to 1.
        """
        options = []
        if bg != -1:
            options.append(f'bgcolor="{bg}"')
        if nb_lig != 1:
            options.append(f'ROWSPAN="{nb_lig}"')
        if nb_col != 1:
            options.append(f'COLSPAN="{nb_col}"')

        options_str = " ".join(options)
        print(f'<TH {options_str}>{content}</TH>')

    def TblStartCell(self, width=-1, height=-1, bg=-1, align=-1, nb_lig=-1, nb_col=-1, class_name=-1):
        """
        Generates the opening <TD> (table data) tag.
        Corresponds to PHP's OV::TblStartCell().

        Args:
            width (int, optional): Width of the cell. Defaults to -1 (not set).
            height (int, optional): Height of the cell. Defaults to -1 (not set).
            bg (str, optional): Background color or image URL. Defaults to -1 (not set).
            align (str, optional): Alignment of content ("center", "bottom", "top", "left", "right"). Defaults to -1 (not set).
            nb_lig (int, optional): ROWSPAN attribute. Defaults to -1 (not set).
            nb_col (int, optional): COLSPAN attribute. Defaults to -1 (not set).
            class_name (str, optional): Class attribute for the cell. Defaults to -1 (not set).
        """
        options = []
        if width != -1:
            options.append(f'WIDTH="{width}"')
        if height != -1:
            options.append(f'HEIGHT="{height}"')

        if bg != -1:
            if bg.startswith("#"):
                options.append(f'BGCOLOR="{bg}"')
            else:
                options.append(f'BACKGROUND="{bg}"')

        if align != -1:
            if align in ["center", "left", "right"]:
                options.append(f'ALIGN="{align}"')
            elif align in ["bottom", "top"]:
                options.append(f'VALIGN="{align}"')

        if nb_lig != -1:
            options.append(f'ROWSPAN="{nb_lig}"')
        if nb_col != -1:
            options.append(f'COLSPAN="{nb_col}"')
        if class_name != -1:
            options.append(f'CLASS="{class_name}"')

        options_str = " ".join(options)
        print(f'<TD {options_str}>')

    def TblEndCell(self):
        """
        Generates the closing </TD> tag.
        Corresponds to PHP's OV::TblEndCell().
        """
        print('</TD>')

    def TblCell(self, content, width=-1, height=-1, bg=-1, align=-1, nb_lig=-1, nb_col=-1, class_name=-1):
        """
        Generates a complete <TD> (table data) tag with content and attributes.
        Corresponds to PHP's OV::TblCell().

        Args:
            content (str): The content of the cell.
            width (int, optional): Width of the cell. Defaults to -1 (not set).
            height (int, optional): Height of the cell. Defaults to -1 (not set).
            bg (str, optional): Background color or image URL. Defaults to -1 (not set).
            align (str, optional): Alignment of content ("center", "bottom", "top", "left", "right"). Defaults to -1 (not set).
            nb_lig (int, optional): ROWSPAN attribute. Defaults to -1 (not set).
            nb_col (int, optional): COLSPAN attribute. Defaults to -1 (not set).
            class_name (str, optional): Class attribute for the cell. Defaults to -1 (not set).
        """
        options = []
        # Background handling (BGCOLOR or BACKGROUND)
        if bg != -1:
            if bg.startswith("#"):
                options.append(f'BGCOLOR="{bg}"')
            else:
                options.append(f'BACKGROUND="{bg}"')

        # Alignment handling (ALIGN or VALIGN)
        if align != -1:
            if align in ["center", "left", "right"]:
                options.append(f'ALIGN="{align}"')
            elif align in ["bottom", "top"]:
                options.append(f'VALIGN="{align}"')

        if width != -1:
            options.append(f'WIDTH="{width}"')
        if height != -1:
            options.append(f'HEIGHT="{height}"')
        if class_name != -1:
            options.append(f'CLASS="{class_name}"')
        if nb_lig != -1:
            options.append(f'ROWSPAN="{nb_lig}"')
        if nb_col != -1:
            options.append(f'COLSPAN="{nb_col}"')

        options_str = " ".join(options)
        print(f'   <TD{options_str}>{content}</TD>')

    def P(self, text, class_name=-1):
        """
        Generates a <P> (paragraph) tag.
        Corresponds to PHP's OV::P().

        Args:
            text (str): The content of the paragraph.
            class_name (str, optional): Class attribute for the paragraph. Defaults to -1 (not set).
        """
        options = ""
        if class_name != -1:
            options = f' CLASS="{class_name}"'
        print(f'<P{options}>{text}</P>')

    def Pre(self, text, width=-1, class_name=-1):
        """
        Generates a <PRE> (preformatted text) tag.
        Corresponds to PHP's OV::Pre().

        Args:
            text (str): The preformatted text content.
            width (int, optional): Width attribute for the tag. Defaults to -1 (not set).
            class_name (str, optional): Class attribute for the tag. Defaults to -1 (not set).
        """
        options = []
        if width != -1:
            options.append(f'WIDTH="{width}"')
        if class_name != -1:
            options.append(f'CLASS="{class_name}"')
        options_str = " ".join(options)
        print(f'<PRE{options_str}>{text}</PRE>')

    def Q(self, text, class_name=-1):
        """
        Generates a <Q> (short quotation) tag.
        Corresponds to PHP's OV::Q().

        Args:
            text (str): The quoted text content.
            class_name (str, optional): Class attribute for the tag. Defaults to -1 (not set).
        """
        options = ""
        if class_name != -1:
            options = f' CLASS="{class_name}"'
        print(f'<Q{options}>{text}</Q>')

    def S(self, text, class_name=-1):
        """
        Generates an <S> (strikethrough) tag.
        Corresponds to PHP's OV::S().

        Args:
            text (str): The text content.
            class_name (str, optional): Class attribute for the tag. Defaults to -1 (not set).
        """
        options = ""
        if class_name != -1:
            options = f' CLASS="{class_name}"'
        print(f'<S{options}>{text}</S>')

    def Samp(self, text, class_name=-1):
        """
        Generates a <SAMP> (sample computer code) tag.
        Corresponds to PHP's OV::Samp().

        Args:
            text (str): The code sample text.
            class_name (str, optional): Class attribute for the tag. Defaults to -1 (not set).
        """
        options = ""
        if class_name != -1:
            options = f' CLASS="{class_name}"'
        print(f'<SAMP{options}>{text}</SAMP>')

    def ScriptS(self, type_attr, language_attr, src_attr):
        """
        Generates one or more <SCRIPT> tags.
        Corresponds to PHP's OV::ScriptS().

        Args:
            type_attr (str): The type attribute for the script (e.g., "text/javascript").
            language_attr (str): The language attribute for the script (e.g., "JavaScript").
            src_attr (str): The src attribute(s) for the script. Can be a single URL or
                            a comma-separated string of URLs (e.g., "url1,url2").
        """
        # PHP's explode('[,]', $src) suggests comma separated
        src_list = src_attr.split('[,]') if '[,]' in src_attr else [src_attr]

        for src in src_list:
            print(f'<SCRIPT LANGUAGE="{language_attr}" TYPE="{type_attr}" src="{src}">')
            print('</SCRIPT>')

    def ScriptEnd(self):
        """
        (Placeholder for PHP's OV::ScriptEnd which was an empty function.)
        This function does nothing, as the <SCRIPT> tag is closed immediately in ScriptS.
        """
        pass # In Python, this is not needed as ScriptS closes the tag.

    def Span(self, text, style=-1, class_name=-1):
        """
        Generates a <SPAN> tag.
        Corresponds to PHP's OV::Span().

        Args:
            text (str): The content of the span.
            style (str, optional): Style attribute for the span. Defaults to -1 (not set).
            class_name (str, optional): Class attribute for the span. Defaults to -1 (not set).
        """
        options = []
        if style != -1:
            options.append(f'STYLE="{style}"')
        if class_name != -1:
            options.append(f'CLASS="{class_name}"')

        options_str = " ".join(options)
        print(f'<SPAN {options_str}>{text}</SPAN>')

    def H(self, text, style=-1, class_name=-1):
        """
        Generates an H1-H6 heading tag.
        Corresponds to PHP's OV::H().

        Args:
            text (str): The heading text.
            style (str, optional): Style attribute for the heading. Defaults to -1 (not set).
            class_name (str, optional): Defines the heading level (e.g., "1" for H1, "2" for H2). Defaults to -1 (H1).
        """
        h_tag = "H1" # Default to H1 if class_name is not a valid level
        if isinstance(class_name, str) and class_name.isdigit() and 1 <= int(class_name) <= 6:
            h_tag = f"H{class_name}"
        elif isinstance(class_name, int) and 1 <= class_name <= 6:
             h_tag = f"H{class_name}"


        options = []
        if style != -1:
            options.append(f'STYLE="{style}"')

        options_str = " ".join(options)
        print(f'<{h_tag} {options_str}>{text}</{h_tag}>')

# Global helper functions that were outside the OV class in PHP but
# are related to its functionality or general HTML/text processing.

def ovl(a, b, c):
    """
    Generates an <a> tag with onmouseover and onmouseout for OverLib tooltips.
    Corresponds to PHP's ovl($a,$b,$c).

    Args:
        a (str): The href URL.
        b (str): The content for the overlib tooltip (passed as a string).
        c (str): The link text.

    Returns:
        str: The generated HTML string for the link with tooltip.
    """
    # Note: `nd()` is typically a JavaScript function provided by overlib.js
    return f'<a href="{a}" onmouseover="return overlib({b});" onmouseout="return nd();">{c}</a>'

def make_bar(str_val):
    """
    Parses a string to create an HTML link with an OverLib tooltip and a line break.
    Corresponds to PHP's make_bar($str).

    Args:
        str_val (str): A string in the format "url,tooltip_content,link_text".

    Returns:
        str: The generated HTML link with tooltip and a <br /> tag.
    """
    try:
        # Assuming the PHP explode('[,]', $str) meant a literal '[,]' separator
        parts = str_val.split('[,]')
        if len(parts) == 3:
            ah, ov, txt = parts
            return ovl(ah, ov, txt) + "<br />"
        else:
            print(f"Warning: make_bar input '{str_val}' did not match expected format.", file=sys.stderr)
            return ""
    except Exception as e:
        print(f"Error in make_bar: {e}", file=sys.stderr)
        return ""

def li(a):
    """
    Generates an <li> (list item) tag.
    Corresponds to PHP's li($a).

    Args:
        a (str): The content of the list item.

    Returns:
        str: The generated HTML string for the list item.
    """
    return f'<li> {a}</li>'

def prpix(img, width, height):
    """
    Prints an HTML <img> tag wrapped in a <div>.
    Corresponds to PHP's prpix().

    Args:
        img (str): Image source URL.
        width (int): Image width.
        height (int): Image height.
    """
    print(f'<div> <img src="{img}" width="{width}" height="{height}"></div>')

def pruff(txt, size):
    """
    Prints a <p> tag with text in a specific font size and black color.
    Corresponds to PHP's pruff().

    Args:
        txt (str): The text content.
        size (int): The font size.
    """
    # PHP code had `str_ireplace("`","",$txt)` which is commented out,
    # so we'll just print directly.
    print(f'<p><font color="000000" size="{size}">{txt}</font></p>')

def pr_html(a, as_return=False):
    """
    Prints (or returns) HTML-escaped content wrapped in <pre> tags.
    Corresponds to PHP's pr_html().

    Args:
        a (any): The content to print (usually an array/list/dict in PHP/Python).
        as_return (bool, optional): If True, returns the string instead of printing. Defaults to False.

    Returns:
        str or int: The HTML string if as_return is True, otherwise 1 (like PHP).
    """
    import html
    output = f"<pre>{html.escape(str(a))}</pre>"
    if as_return:
        return output
    else:
        print(output)
        return 1

def Pad(string, pad):
    """
    Repeats a string a given number of times.
    Corresponds to PHP's Pad().

    Args:
        string (str): The string to repeat.
        pad (int): The number of times to repeat.

    Returns:
        str: The repeated string.
    """
    return string * pad

def getCSVValue(string, separator=","):
    """
    Parses a CSV string, handling quotes and delimiters.
    Corresponds to PHP's getCSVValue().
    NOTE: This is a direct Python adaptation of the PHP logic.
    For robust CSV parsing in Python, the 'csv' module is usually preferred.

    Args:
        string (str): The CSV string to parse.
        separator (str, optional): The delimiter. Defaults to ",".

    Returns:
        list[str]: A list of parsed elements.
    """
    elements = []
    in_quote = False
    current_element = []
    i = 0
    while i < len(string):
        char = string[i]
        if char == '"':
            if in_quote and (i + 1 < len(string) and string[i+1] == '"'):
                # Escaped quote: "" becomes "
                current_element.append('"')
                i += 1 # Skip the next quote
            else:
                in_quote = not in_quote
        elif char == separator and not in_quote:
            elements.append("".join(current_element))
            current_element = []
        else:
            current_element.append(char)
        i += 1
    elements.append("".join(current_element)) # Add the last element

    # Clean up quotes from the resulting elements (as PHP did)
    cleaned_elements = []
    for element in elements:
        # Check for surrounding quotes after parsing
        if len(element) > 1 and element[0] == '"' and element[-1] == '"':
            element = element[1:-1] # Remove outer quotes
            element = element.replace('""', '"') # Handle escaped quotes
        cleaned_elements.append(element)
    return cleaned_elements


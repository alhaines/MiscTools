#!/home/al/miniconda3/envs/py/bin/python3
# -*- coding: utf-8 -*-
#
#  filename:   /home/al/projects/mediaplayerv1/OV.py
#
#  Copyright 2025 AL Haines
#
#  Definitive Version: Correctly implements track number sorting
#                      AND the resume playback functionality.

from flask import render_template, jsonify, request, Response, stream_with_context, session
import os
import re
import subprocess
from MySql import MySQL
import config
try:
    from MySql import MySQL
    import config
except Exception as e:
    raise ImportError(f"OV.py failed to load dependencies: {e}") from e

try:
    from rich.console import Console
except ImportError as e:
    raise ImportError(f"OV.py failed to load Rich: {e}") from e

CONSOLE = Console()


def check_root():
    """Ensure the caller has permission to modify GRUB configuration."""
    if os.geteuid() != 0:
        CONSOLE.print("[bold red]ERROR: This script must be run as root (sudo) to edit GRUB configuration files and trigger updates.[/bold red]")
        raise PermissionError("Root privileges are required to modify GRUB configuration")


def get_partition_uuid(path):
    """Return the filesystem UUID for the partition containing path."""
    try:
        df_output = subprocess.check_output(["df", "--output=source", path], text=True)
        device = df_output.strip().split("\n")[-1]
        uuid_output = subprocess.check_output(
            ["blkid", "-o", "value", "-s", "UUID", device], text=True
        )
        return uuid_output.strip()
    except Exception as exc:
        CONSOLE.print(f"[yellow]Warning: Could not auto-detect UUID ({exc}).[/yellow]")
        return None


def get_iso_list(directory):
    """Return ISO files in directory, including symlinks resolving to ISO files."""
    if not os.path.exists(directory):
        raise FileNotFoundError(f"Target directory '{directory}' does not exist")

    iso_files = []
    for filename in sorted(os.listdir(directory)):
        full_path = os.path.join(directory, filename)
        is_iso = filename.lower().endswith(".iso")
        is_iso_link = os.path.islink(full_path) and os.path.realpath(full_path).lower().endswith(".iso")
        if is_iso or is_iso_link:
            iso_files.append({
                "filename": filename,
                "size_mb": os.path.getsize(full_path) / (1024 * 1024),
            })
    return iso_files


def generate_grub_entry(iso_name, uuid):
    """Build a GRUB loopback menu entry for a supported live ISO."""
    name_lower = iso_name.lower()
    header = f'menuentry "Live ISO: {iso_name} (Loopback)" --class os_icon {{\n'
    modules = "    insmod part_gpt\n    insmod ext2\n"
    search_line = f"    search --no-floppy --fs-uuid --set=root {uuid}\n"
    set_iso = f'    set isofile="/ISO/{iso_name}"\n'
    loop_line = "    loopback loop ($root)$isofile\n"

    if "debian" in name_lower:
        linux_line = "    linux (loop)/live/vmlinuz boot=live findiso=$isofile quiet splash\n"
        initrd_line = "    initrd (loop)/live/initrd.img\n"
    elif "linuxmint" in name_lower or "lmde" in name_lower:
        linux_line = "    linux (loop)/casper/vmlinuz boot=casper iso-scan/filename=$isofile quiet splash\n"
        initrd_line = "    initrd (loop)/casper/initrd.lz\n"
    elif "fedora" in name_lower or "bazzite" in name_lower:
        probe_line = "    probe --set=isolabel --label (loop)\n"
        linux_line = "    linux (loop)/boot/x86_64/loader/linux root=live:CDLABEL=$isolabel rd.live.image iso-scan/filename=$isofile quiet splash\n"
        initrd_line = "    initrd (loop)/boot/x86_64/loader/initrd\n"
        return header + modules + search_line + set_iso + loop_line + probe_line + linux_line + initrd_line + "}\n"
    elif "android" in name_lower:
        linux_line = "    linux (loop)/kernel root=/dev/ram0 androidboot.selinux=permissive buildvariant=userdebug SRC= DATA=\n"
        initrd_line = "    initrd (loop)/initrd.img\n"
    else:
        linux_line = "    linux (loop)/casper/vmlinuz boot=casper iso-scan/filename=$isofile quiet splash\n"
        initrd_line = "    initrd (loop)/casper/initrd\n"

    return header + modules + search_line + set_iso + loop_line + linux_line + initrd_line + "}\n"


def _replace_or_append_grub_entry(existing_text, entry_text):
    """Replace one generated Live ISO entry while preserving all other content."""
    entry_header = re.match(r'^menuentry "Live ISO: .*? \(Loopback\)".*\{$', entry_text, re.MULTILINE)
    if not entry_header:
        raise ValueError("Entry text does not contain a generated Live ISO menuentry")
    target_header = entry_header.group(0)
    lines = existing_text.splitlines(keepends=True)
    output = []
    index = 0
    replaced = False
    while index < len(lines):
        if lines[index].rstrip("\n") == target_header:
            depth = 0
            while index < len(lines):
                depth += lines[index].count("{") - lines[index].count("}")
                index += 1
                if depth <= 0:
                    break
            output.append(entry_text if entry_text.endswith("\n") else entry_text + "\n")
            replaced = True
        else:
            output.append(lines[index])
            index += 1
    if not replaced:
        if output and not output[-1].endswith("\n"):
            output[-1] += "\n"
        output.append("\n" + (entry_text if entry_text.endswith("\n") else entry_text + "\n"))
    return "".join(output)


def write_grub_config(entry_text, grub_file="/etc/grub.d/40_custom"):
    """Add or replace one generated entry without deleting existing GRUB entries."""
    base_template = "#!/bin/sh\nexec tail -n +3 $0\n"
    try:
        try:
            with open(grub_file, encoding="utf-8") as config_file:
                existing_text = config_file.read()
        except FileNotFoundError:
            existing_text = base_template
        updated_text = _replace_or_append_grub_entry(existing_text, entry_text)
        with open(grub_file, "w", encoding="utf-8") as config_file:
            config_file.write(updated_text)
        CONSOLE.print(f"[bold green]Updated {grub_file} while preserving existing entries[/bold green]")
    except (IOError, ValueError) as exc:
        CONSOLE.print(f"[bold red]FATAL: GRUB configuration update failed: {exc}[/bold red]")
        raise


def run_grub_update():
    """Run the host system's GRUB configuration compiler."""
    CONSOLE.print("[bold yellow]Compiling GRUB configuration...[/bold yellow]")
    command = "update-grub" if subprocess.call(["which", "update-grub"], stdout=subprocess.DEVNULL) == 0 else "update-grub2"
    try:
        subprocess.run([command], check=True, text=True, capture_output=True)
    except subprocess.CalledProcessError as exc:
        CONSOLE.print(f"[bold red]GRUB update failed:[/bold red]\n{exc.stderr}")
        raise
    CONSOLE.print("[bold green]GRUB configuration compiled successfully![/bold green]")
def _get_db_connection():
    return MySQL(**config.mysql_config)

def _check_content_access(category, user_level):
    """
    Check if user has sufficient level to access content in this category.

    Args:
        category: The category/table name (e.g., 'movies', 'xxx')
        user_level: The user's level from session (1, 2, or 3)

    Returns:
        tuple: (allowed: bool, min_level: int, message: str)
    """
    db = _get_db_connection()

    # Check if category has a level in table_data
    query = "SELECT level FROM table_data WHERE `table` = %s"
    result = db.get_data(query, (category,))

    if result:
        min_level = result[0]['level']
        if user_level >= min_level:
            return True, min_level, "Access granted"
        else:
            return False, min_level, f"Access denied - Level {min_level} required"
    else:
        # No rating found - default to allow (level 1)
        return True, 1, "No rating found - access granted"

def _log_playback_activity(table_name, item_id, item_details, resume_position=0.0, duration=0.0):
    """
    Log user playback activity to media_playback_history table.

    Args:
        table_name: The category/table name (e.g., 'movies', 'audio_audiobooks')
        item_id: The media item ID
        item_details: Dict with title, file_path, album (if available)
        resume_position: Current playback position in seconds
        duration: Total media duration in seconds
    """
    # Get user info from session
    user_id = session.get('user_id')
    username = session.get('username', 'unknown')
    user_level = session.get('level', 0)

    if not user_id:
        return  # Don't log if user not authenticated

    db = _get_db_connection()

    # Calculate percentage watched and completion status
    percent_watched = 0.0
    completed = False
    if duration > 0:
        percent_watched = (resume_position / duration) * 100
        completed = percent_watched >= 95.0

    # Extract media details
    title = item_details.get('title', 'Unknown')
    file_path = item_details.get('file_path', '')
    album = item_details.get('album', None)

    # Insert or update activity record
    query = """
        INSERT INTO media_playback_history
        (user_id, username, user_level, category, media_id, title, file_path, album,
         resume_position, duration, percent_watched, completed)
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
        ON DUPLICATE KEY UPDATE
            resume_position = VALUES(resume_position),
            duration = VALUES(duration),
            percent_watched = VALUES(percent_watched),
            completed = VALUES(completed),
            last_updated = CURRENT_TIMESTAMP
    """

    try:
        db.put_data(query, (
            user_id, username, user_level, table_name, item_id,
            title, file_path, album, resume_position, duration,
            percent_watched, completed
        ))
    except Exception as e:
        # Log error but don't break playback functionality
        print(f"Error logging playback activity: {e}")

def _get_item_details(table_name, item_id):
    db = _get_db_connection()
    query = f"SELECT * FROM `{table_name}` WHERE id = %s"
    results = db.get_data(query, (item_id,))
    return results[0] if results else None

def get_resume_items():
    """
    Get resume items for the currently logged-in user from media_playback_history.
    Only shows items that are in progress (not completed, >0% watched).
    """
    db = _get_db_connection()

    # Get current user ID from session
    user_id = session.get('user_id')
    if not user_id:
        return []  # No user logged in, return empty list

    # Query media_playback_history for this user's in-progress items
    query = """
        SELECT
            media_id as id,
            title,
            file_path,
            album,
            category,
            last_updated as last_played,
            resume_position,
            percent_watched,
            duration
        FROM media_playback_history
        WHERE user_id = %s
            AND completed = FALSE
            AND percent_watched > 0.1
            AND percent_watched < 95.0
        ORDER BY last_updated DESC
        LIMIT 20
    """

    return db.get_data(query, (user_id,))

def update_resume_position(table_name, item_id, position, duration):
    db = _get_db_connection()
    position_to_save = float(position)
    duration_float = float(duration)

    if (duration_float - position_to_save) < 15:
        position_to_save = 0

    # Update the media table with resume position
    query = f"UPDATE `{table_name}` SET resume_position = %s, last_played = NOW() WHERE id = %s"
    db.put_data(query, (position_to_save, item_id))

    # Log user activity
    item_details = _get_item_details(table_name, item_id)
    if item_details:
        _log_playback_activity(table_name, item_id, item_details, position_to_save, duration_float)

    return jsonify(status='success')

def clear_resume_position(table_name, item_id):
    db = _get_db_connection()
    query = f"UPDATE `{table_name}` SET resume_position = 0 WHERE id = %s"
    db.put_data(query, (item_id,))
    return jsonify(status='success')

def render_index_page():
    db = _get_db_connection()

    # Fetch table lists from the database
    try:
        all_tables_data = db.get_data("SELECT title, `table` FROM als.table_data ORDER BY title")

        if not all_tables_data:
            raise ValueError("No tables found in als.table_data")

    except Exception as e:
        # Fallback to config if table doesn't exist or is empty
        print(f"Could not fetch from table_data, falling back to config: {e}")
        all_table_names_from_config = [row[1] for row in config.table_list]
        all_tables_data = [{'title': t.replace('_', ' ').title(), 'table': t} for t in all_table_names_from_config]

    # Filter categories based on user's access level
    user_level = session.get('level', 0)
    accessible_categories = []
    for item in all_tables_data:
        allowed, _, _ = _check_content_access(item['table'], user_level)
        if allowed:
            accessible_categories.append(item)

    resume_items = get_resume_items()

    # Get username from session
    username = session.get('username', 'Guest')

    # Pass the categories list to the template
    return render_template('index.html', categories=accessible_categories, resume_items=resume_items,
                         username=username)

def get_folders_for_table(table_name):
    db = _get_db_connection()
    query = f"SELECT DISTINCT SUBSTRING_INDEX(SUBSTRING_INDEX(file_path, '/', 6), '/', -1) AS folder FROM `{table_name}`"
    results = db.get_data(query)
    folders = [row['folder'] for row in results if row['folder']]
    folders.sort()
    return jsonify(folders)

def get_videos_for_folder(table_name, folder):
    db = _get_db_connection()
    # Match folder and all sub-folders by using pattern that matches folder name followed by / or end of path segment
    # Special case: if folder is 'all', return all videos
    if folder == 'all':
        query = f"SELECT id, title, file_path, resume_position FROM `{table_name}` ORDER BY title ASC"
        videos = db.get_data(query)
    else:
        query = f"SELECT id, title, file_path, resume_position FROM `{table_name}` WHERE file_path LIKE %s ORDER BY title ASC"
        videos = db.get_data(query, (f'%/{folder}/%',))
    return jsonify(videos)

def get_albums_for_table(table_name):
    db = _get_db_connection()
    #query = f"SELECT DISTINCT album FROM `{table_name}` WHERE album IS NOT NULL ORDER BY album ASC"
    query = f"SELECT DISTINCT album FROM `{table_name}` ORDER BY album ASC"
    results = db.get_data(query)
    albums = [row['album'] for row in results] if results else []
    return jsonify(albums)

def get_tracks_for_album(table_name, album):
    db = _get_db_connection()
    columns = db.get_field_names(table_name)
    # FIX: Only order by track_number if the column exists in the table.
    order_by_clause = "track_number, title ASC" if 'track_number' in columns else "title ASC"
    query = f"SELECT id, title, resume_position FROM `{table_name}` WHERE album = %s ORDER BY {order_by_clause}"
    tracks = db.get_data(query, (album,))
    return jsonify(tracks)

def get_random_musicvid():
    """Get a random music video from the musicvids/Videos folder."""
    db = _get_db_connection()
    query = """
        SELECT id FROM musicvids
        WHERE file_path LIKE '%/Videos/%'
        ORDER BY RAND()
        LIMIT 1
    """
    result = db.get_data(query)
    if result:
        return jsonify({'id': result[0]['id'], 'table': 'musicvids'})
    return jsonify({'error': 'No music videos found'}), 404

def get_random_song():
    """Get a random song from the audio_music table."""
    db = _get_db_connection()
    query = "SELECT id FROM audio_music ORDER BY RAND() LIMIT 1"
    result = db.get_data(query)
    if result:
        return jsonify({'id': result[0]['id'], 'table': 'audio_music'})
    return jsonify({'error': 'No songs found'}), 404

def render_admin_page():
    """Render the administration page."""
    db = _get_db_connection()

    # Get all users
    users = db.get_data("SELECT id, username, level FROM users ORDER BY username")

    # Get all categories with their minimum access level and friendly title
    # This joins the list of all possible tables with their ratings and titles
    all_tables_from_config = [row[1] for row in config.table_list]

    # Create a temporary table-like structure in the query
    placeholders = ', '.join(['%s'] * len(all_tables_from_config))

    query = f"""
        SELECT
            t.table_name AS category,
            COALESCE(cr.min_level, 1) AS min_level,
            COALESCE(tt.title, t.table_name) AS title
        FROM
            (SELECT unnest(array[{placeholders}]) AS table_name) AS t
        LEFT JOIN content_ratings cr ON t.table_name = cr.category
        LEFT JOIN table_titles tt ON t.table_name = tt.table_name
        ORDER BY t.table_name;
    """
    # Note: The above query uses PostgreSQL's unnest function syntax as a placeholder.
    # Since the DB is MySQL, we'll build the data manually.

    categories = []
    for table_name in all_tables_from_config:
        table_data_q = db.get_data("SELECT title, level FROM table_data WHERE `table` = %s", (table_name,))

        if table_data_q:
            min_level = table_data_q[0]['level']
            title = table_data_q[0]['title']
        else:
            min_level = 1
            title = table_name.replace('_', ' ').title()

        categories.append({
            'category': table_name,
            'min_level': min_level,
            'title': title
        })

    db_name = config.mysql_config['database']
    return render_template('admin.html', users=users, categories=categories, db_name=db_name)

def set_user_level():
    """Update a user's access level."""
    data = request.get_json()
    user_id = data.get('user_id')
    level = data.get('level')

    if not all([user_id, level]):
        return jsonify(error="Missing user_id or level"), 400

    db = _get_db_connection()
    query = "UPDATE users SET level = %s WHERE id = %s"
    db.put_data(query, (level, user_id))

    return jsonify(status="success")

def set_category_level():
    """Update a category's minimum access level."""
    data = request.get_json()
    category = data.get('category')
    min_level = data.get('min_level')

    if not all([category, min_level]):
        return jsonify(error="Missing category or min_level"), 400

    db = _get_db_connection()
    query = "UPDATE table_data SET level = %s WHERE `table` = %s"
    db.put_data(query, (min_level, category))

    return jsonify(status="success")

def set_category_title():
    """Update a category's friendly title."""
    data = request.get_json()
    category = data.get('category')
    title = data.get('title')

    if not all([category, title]):
        return jsonify(error="Missing category or title"), 400

    db = _get_db_connection()
    query = "UPDATE table_data SET title = %s WHERE `table` = %s"
    db.put_data(query, (title, category))

    return jsonify(status="success", new_title=title)

def zero_resume_positions():
    """Clear resume positions for items watched less than a certain time."""
    data = request.get_json()
    max_minutes = data.get('max_minutes', 5)
    max_seconds = int(max_minutes) * 60

    db = _get_db_connection()

    # Find all tables in the database
    all_tables_raw = db.get_data("SHOW TABLES")
    all_tables = [list(t.values())[0] for t in all_tables_raw]

    cleared_count = 0
    for table in all_tables:
        # Check if the table has 'resume_position' and 'duration' columns
        columns = [c['Field'] for c in db.get_data(f"DESCRIBE `{table}`")]
        if 'resume_position' in columns and 'duration' in columns:
            query = f"""
                UPDATE `{table}`
                SET resume_position = 0
                WHERE resume_position > 0 AND resume_position < %s
            """
            # The result of put_data for an UPDATE is the number of rows affected
            cleared_count += db.put_data(query, (max_seconds,))

    return jsonify(status="success", cleared_count=cleared_count)


def render_player_page(table_name, item_id):
    # Check content access level
    user_level = session.get('level', 0)
    allowed, min_level, message = _check_content_access(table_name, user_level)

    if not allowed:
        return f"""
        <html>
        <head>
            <title>Access Denied</title>
            <link rel="stylesheet" href="/static/styles.css">
        </head>
        <body>
            <div style="max-width: 600px; margin: 100px auto; padding: 40px; background: #f8d7da; border: 2px solid #f5c6cb; border-radius: 10px; text-align: center;">
                <h1 style="color: #721c24;">🚫 Access Denied</h1>
                <p style="font-size: 18px; color: #721c24; margin: 20px 0;">
                    This content requires Level {min_level} access.
                </p>
                <p style="color: #856404;">Your current level: {user_level}</p>
                <p style="margin-top: 30px;">
                    <a href="/" style="padding: 12px 24px; background: #007bff; color: white; text-decoration: none; border-radius: 5px; display: inline-block;">
                        « Back to Home
                    </a>
                </p>
            </div>
        </body>
        </html>
        """, 403

    current_item = _get_item_details(table_name, item_id)
    if not current_item:
        return "Media item not found", 404

    # Log that user started playing this media (initial log with 0 position)
    _log_playback_activity(table_name, item_id, current_item, resume_position=0.0, duration=0.0)

    db = _get_db_connection()
    playlist, current_track_index = [], -1
    columns = db.get_field_names(table_name) # Get column names for conditional ordering

    # Logic to build playlist based on media type
    if 'album' in current_item and current_item['album'] is not None:
        # FIX: Only order by track_number if the column exists in the table.
        order_by_clause = "track_number, title ASC" if 'track_number' in columns else "title ASC"
        query = f"SELECT id, title FROM `{table_name}` WHERE album = %s ORDER BY {order_by_clause}"
        playlist = db.get_data(query, (current_item['album'],))
    elif 'file_path' in current_item:
        folder = os.path.basename(os.path.dirname(current_item['file_path']))
        query = f"SELECT id, title, file_path FROM `{table_name}` WHERE file_path LIKE %s ORDER BY title ASC"
        playlist = db.get_data(query, (f'%/{folder}/%',))

    if playlist:
        for i, track in enumerate(playlist):
            if track['id'] == item_id:
                current_track_index = i
                break

    file_path = current_item.get('file_path', '')
    is_audio = file_path.endswith(('.mp3', '.m4a', '.wav', '.flac'))

    # Get username from session for display
    user_name = session.get('username', 'Guest')

    return render_template('player.html',
                           item=current_item,
                           category=table_name,
                           playlist=playlist,
                           current_track_index=current_track_index,
                           is_audio=is_audio,
                           user_name=user_name)

def stream_with_range_support(table_name, item_id):
    item = _get_item_details(table_name, item_id)
    if not (item and item.get('file_path')):
        return "File path not found", 404
    path = item['file_path']
    if not os.path.exists(path):
        return "File on disk not found", 404
    file_size = os.path.getsize(path)
    range_header = request.headers.get('Range', None)

    file_extension = os.path.splitext(path)[1].lower()
    if file_extension in ['.mp3', '.m4a', '.wav', '.flac']:
        mime_type = 'audio/mpeg'
    elif file_extension in ['.mp4', '.mkv', '.avi', '.mov']:
        mime_type = 'video/mp4'
    else:
        mime_type = 'application/octet-stream'

    def generate_chunks(file, start, length):
        with file:
            file.seek(start)
            remaining = length
            while remaining > 0:
                chunk_size = min(remaining, 1024 * 1024)
                data = file.read(chunk_size)
                if not data: break
                yield data
                remaining -= len(data)

    if range_header:
        byte1, byte2 = 0, None
        m = re.search(r'(\d+)-(\d*)', range_header)
        g = m.groups()
        if g[0]: byte1 = int(g[0])
        if g[1]: byte2 = int(g[1])
        if byte2 is None: byte2 = file_size - 1
        length = byte2 - byte1 + 1
        resp = Response(
            stream_with_context(generate_chunks(open(path, 'rb'), byte1, length)),
            206,
            mimetype=mime_type,
            direct_passthrough=True
        )
        resp.headers.add('Content-Range', f'bytes {byte1}-{byte2}/{file_size}')
        return resp
    else:
        resp = Response(
            stream_with_context(generate_chunks(open(path, 'rb'), 0, file_size)),
            200,
            mimetype=mime_type,
            direct_passthrough=True
        )
        resp.headers.add('Content-Length', file_size)
        return resp

def render_viewing_report():
    """
    Generate a viewing report showing what each user has watched.
    Restricted to level 3 users only.
    """
    db = _get_db_connection()

    # Get all users who have viewing history
    query = """
        SELECT DISTINCT user_id, username, user_level
        FROM media_playback_history
        ORDER BY username
    """
    users = db.get_data(query)

    # For each user, get their viewing history
    user_reports = []
    for user in users:
        user_query = """
            SELECT
                title,
                category,
                percent_watched,
                completed,
                last_updated
            FROM media_playback_history
            WHERE user_id = %s
            ORDER BY last_updated DESC
            LIMIT 50
        """
        viewing_history = db.get_data(user_query, (user['user_id'],))
        user_reports.append({
            'user_id': user['user_id'],
            'username': user['username'],
            'user_level': user['user_level'],
            'history': viewing_history
        })

    return render_template('viewing_report.html', user_reports=user_reports)

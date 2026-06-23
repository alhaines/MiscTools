#!/home/al/miniconda3/envs/py/bin/python3
# -*- coding: utf-8 -*-
#
# filename:   /home/al/py/bootiso.py
#
# Copyright 2026 AL Haines
# Coding by AI Collaborator
#
# Description: A Python and Rich-based boot menu shell script,
# select iso from listing than edit grub with selection

import os
import re
import sys
import subprocess

try:
    from rich.console import Console
    from rich.table import Table
except ImportError:
    print("FATAL: The 'rich' library is required. Please run 'pip install rich'.", file=sys.stderr)
    sys.exit(1)

CONSOLE = Console()
ISO_DIR = "/ISO"
CUSTOM_GRUB_FILE = "/etc/grub.d/40_custom"

def check_root():
    """Ensure the script runs with elevated privileges to modify GRUB configs."""
    if os.geteuid() != 0:
        CONSOLE.print("[bold red]ERROR: This script must be run as root (sudo) to edit GRUB configuration files and trigger updates.[/bold red]")
        sys.exit(1)

def get_partition_uuid(path):
    """Retrieve the UUID of the partition hosting the specified directory path."""
    try:
        # Find the device holding the directory path
        df_output = subprocess.check_output(["df", "--output=source", path], text=True)
        device = df_output.strip().split("\n")[-1]

        # Get the UUID via blkid
        uuid_output = subprocess.check_output(["blkid", "-o", "value", "-s", "UUID", device], text=True)
        return uuid_output.strip()
    except Exception as e:
        CONSOLE.print(f"[yellow]Warning: Could not auto-detect UUID ({e}). Using root drive fallback.[/yellow]")
        return None

def get_iso_list(directory):
    """Scan directory and return a structured list of available ISO files, filtering out paths."""
    if not os.path.exists(directory):
        CONSOLE.print(f"[bold red]ERROR: Target directory '{directory}' does not exist.[/bold red]")
        sys.exit(1)

    files = sorted(os.listdir(directory))
    iso_files = []
    for f in files:
        full_path = os.path.join(directory, f)
        if f.lower().endswith(".iso") or (os.path.islink(full_path) and os.path.realpath(full_path).lower().endswith(".iso")):
            size_mb = os.path.getsize(full_path) / (1024 * 1024)
            iso_files.append({"filename": f, "size_mb": size_mb})
    return iso_files

def generate_grub_entry(iso_name, uuid):
    """Build a specialized GRUB loopback entry string tailored to target distributions."""
    name_lower = iso_name.lower()

    header = f'menuentry "Live ISO: {iso_name} (Loopback)" --class os_icon {{\n'
    modules = '    insmod part_gpt\n    insmod ext2\n'
    search_line = f'    search --no-floppy --fs-uuid --set=root {uuid}\n'
    set_iso = f'    set isofile="/ISO/{iso_name}"\n'
    loop_line = '    loopback loop ($root)$isofile\n'

    if "linuxmint" in name_lower or "lmde" in name_lower or "debian" in name_lower:
        linux_line = '    linux (loop)/casper/vmlinuz boot=casper iso-scan/filename=$isofile quiet splash\n'
        initrd_line = '    initrd (loop)/casper/initrd.lz\n'
        if "debian" in name_lower:
            linux_line = '    linux (loop)/live/vmlinuz boot=live findiso=$isofile quiet splash\n'
            initrd_line = '    initrd (loop)/live/initrd.img\n'

    elif "fedora" in name_lower or "bazzite" in name_lower:
        # Probe the loop device at boot to dynamically find and map the precise filesystem volume CDLABEL
        probe_line = '    probe --set=isolabel --label (loop)\n'
        linux_line = f'    linux (loop)/boot/x86_64/loader/linux root=live:CDLABEL=$isolabel rd.live.image iso-scan/filename=$isofile quiet splash\n'
        initrd_line = '    initrd (loop)/boot/x86_64/loader/initrd\n'
        return header + modules + search_line + set_iso + loop_line + probe_line + linux_line + initrd_line + '}\n'

    elif "android" in name_lower:
        linux_line = '    linux (loop)/kernel root=/dev/ram0 androidboot.selinux=permissive buildvariant=userdebug SRC= DATA=\n'
        initrd_line = '    initrd (loop)/initrd.img\n'

    else:
        linux_line = '    linux (loop)/casper/vmlinuz boot=casper iso-scan/filename=$isofile quiet splash\n'
        initrd_line = '    initrd (loop)/casper/initrd\n'

    footer = '}\n'
    return header + modules + search_line + set_iso + loop_line + linux_line + initrd_line + footer

def write_grub_config(entry_text):
    """Safely rewrite 40_custom using standard structural preservation protocols."""
    base_template = (
        "#!/bin/sh\n"
        "exec tail -n +3 $0\n"
        "# This file provides an easy way to add custom menu entries.  Simply type the\n"
        "# menu entries you want to add after this comment.  Be careful not to change\n"
        "# the 'exec tail' line above.\n"
    )

    try:
        with open(CUSTOM_GRUB_FILE, "w") as f:
            f.write(base_template + "\n" + entry_text)
        CONSOLE.print(f"[bold green]Successfully updated configuration content inside {CUSTOM_GRUB_FILE}[/bold green]")
    except IOError as e:
        CONSOLE.print(f"[bold red]FATAL: File system modification failed: {e}[/bold red]")
        sys.exit(1)

def run_grub_update():
    """Execute the host systems standard boot loader compilation tool chains."""
    CONSOLE.print("[bold yellow]Compiling configuration paths... (Running update-grub)[/bold yellow]")
    try:
        command = "update-grub" if subprocess.call(["which", "update-grub"], stdout=subprocess.DEVNULL) == 0 else "update-grub2"
        subprocess.run([command], check=True, text=True, capture_output=True)
        CONSOLE.print("[bold green]GRUB sequence recompiled successfully![/bold green]")
    except subprocess.CalledProcessError as e:
        CONSOLE.print(f"[bold red]Compilation error executing GRUB configuration updates:[/bold red]\n{e.stderr}")
        sys.exit(1)

def main():
    check_root()
    uuid = get_partition_uuid(ISO_DIR)
    if not uuid:
        CONSOLE.print("[bold red]FATAL: Partition UUID mapping check failed. Aborting script execution.[/bold red]")
        sys.exit(1)

    iso_list = get_iso_list(ISO_DIR)

    if not iso_list:
        CONSOLE.print(f"[bold yellow]No bootable configuration images discovered inside path: {ISO_DIR}[/bold yellow]")
        sys.exit(0)

    table = Table(title="Available ISO Images mapped in /ISO", show_header=True, header_style="bold cyan")
    table.add_column("Key Index", style="bold green", justify="center", width=10)
    table.add_column("ISO Target File Name", style="white")
    table.add_column("File Capacity", justify="right", style="magenta")

    for index, iso in enumerate(iso_list):
        table.add_row(str(index + 1), iso["filename"], f"{iso['size_mb']:.1f} MB")

    CONSOLE.print(table)

    try:
        user_input = input(f"\nSelect target index sequence entry to mount (1-{len(iso_list)}) or 'q' to abort: ").strip()
        if user_input.lower() == 'q':
            CONSOLE.print("[yellow]Operation aborted by operator instruction.[/yellow]")
            sys.exit(0)

        selection = int(user_input) - 1
        if selection < 0 or selection >= len(iso_list):
            raise ValueError
    except (ValueError, IndexError):
        CONSOLE.print("[bold red]Invalid selection sequence array mapping context index defined.[/bold red]")
        sys.exit(1)

    selected_iso = iso_list[selection]["filename"]
    CONSOLE.print(f"\n[bold green]Processing boot sequence profiles target context for: {selected_iso}[/bold green]")

    grub_entry = generate_grub_entry(selected_iso, uuid)
    write_grub_config(grub_entry)
    run_grub_update()

if __name__ == "__main__":
    main()

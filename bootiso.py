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
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import OV

try:
    from rich.console import Console
    from rich.table import Table
except ImportError:
    print("FATAL: The 'rich' library is required. Please run 'pip install rich'.", file=sys.stderr)
    sys.exit(1)

CONSOLE = Console()
ISO_DIR = "/ISO"

def main():
    OV.check_root()
    uuid = OV.get_partition_uuid(ISO_DIR)
    if not uuid:
        CONSOLE.print("[bold red]FATAL: Partition UUID mapping check failed. Aborting script execution.[/bold red]")
        sys.exit(1)

    iso_list = OV.get_iso_list(ISO_DIR)

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

    grub_entry = OV.generate_grub_entry(selected_iso, uuid)
    OV.write_grub_config(grub_entry)
    OV.run_grub_update()

if __name__ == "__main__":
    main()

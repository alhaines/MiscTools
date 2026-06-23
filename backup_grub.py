#!/home/al/miniconda3/envs/py/bin/python3
# -*- coding: utf-8 -*-
#
# filename:   /home/al/py/backup_grub.py
#
# Copyright 2026 AL Haines
# Coding by AI Collaborator
#
# Description: Automates timestamped snapshot backups of critical
# GRUB structural files and custom source menu scripts.

import os
import sys
import tarfile
from datetime import datetime

try:
    from rich.console import Console
except ImportError:
    print("FATAL: The 'rich' library is required. Please run 'pip install rich'.", file=sys.stderr)
    sys.exit(1)

CONSOLE = Console()
BACKUP_DIR = "/home/al/backups"
TARGET_FILES = [
    "/etc/default/grub",
    "/etc/grub.d/40_custom"
]

def check_root():
    """Ensure script is running with privileges necessary to access system configurations."""
    if os.geteuid() != 0:
        CONSOLE.print("[bold red]ERROR: Privileged system access required. Please execute this utility using sudo.[/bold red]")
        sys.exit(1)

def ensure_backup_directory():
    """Verify target destination path exists or build the storage directory structure safely."""
    if not os.path.exists(BACKUP_DIR):
        try:
            os.makedirs(BACKUP_DIR, exist_ok=True)
            # Ensure ownership parameters match the user profile path contexts
            os.chown(BACKUP_DIR, 1000, 1000)
            CONSOLE.print(f"[green]Created backup storage path destination directory: {BACKUP_DIR}[/green]")
        except Exception as e:
            CONSOLE.print(f"[bold red]FATAL: Failed to initialize storage paths: {e}[/bold red]")
            sys.exit(1)

def execute_snapshot():
    """Pack and compress defined active configurations into a timestamped archive."""
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    archive_filename = f"grub_config_backup_{timestamp}.tar.gz"
    archive_path = os.path.join(BACKUP_DIR, archive_filename)

    CONSOLE.print("[yellow]Reading current active system boot layouts...[/yellow]")

    try:
        with tarfile.open(archive_path, "w:gz") as tar:
            for target in TARGET_FILES:
                if os.path.exists(target):
                    # Preserve path structures natively inside the archive root block mappings
                    tar.add(target)
                    CONSOLE.print(f" -> Added configuration file payload path: [cyan]{target}[/cyan]")
                else:
                    CONSOLE.print(f"[yellow]Warning: Expected target file context not discovered: {target}[/yellow]")

        # Set user permissions on generated archive files
        os.chown(archive_path, 1000, 1000)
        os.chmod(archive_path, 0o644)

        CONSOLE.print(f"\n[bold green]Success! GRUB configuration state archived cleanly to:[/bold green]")
        CONSOLE.print(f"[bold white]{archive_path}[/bold white]\n")

    except Exception as e:
        CONSOLE.print(f"[bold red]FATAL: Archive generation pipeline failure encountered: {e}[/bold red]")
        sys.exit(1)

def main():
    check_root()
    ensure_backup_directory()
    execute_snapshot()

if __name__ == "__main__":
    main()

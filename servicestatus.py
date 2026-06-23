#!/home/al/miniconda3/envs/py/bin/python3
# -*- coding: utf-8 -*-
#
# filename:   /home/al/py/servicestatus.py
#
# Copyright 2025 AL Haines
#
# Description: A CLI tool to display the status of a predefined list of
#              systemd services in a clean, rich-formatted table.
# v2.0: Added Port detection for web services.

import subprocess
import re
import sys
import socket

try:
    from rich.console import Console
    from rich.table import Table
except ImportError:
    print("FATAL: The 'rich' library is required. Please run 'pip install rich'.", file=sys.stderr)
    sys.exit(1)

#     "mediamanager.service",
SERVICE_LIST = [
    "cloudflared.service",
    "addressbookv2.service",
    "webmin.service",
    "audio.service",
    "navidrome.service",
    "rclone-gdrive.service",
    "dash_admin.service",
    "filebrowser.service",
    "mediaplayer.service",
    "techblog.service",
    "login.service",
]

def get_service_status(service_name):
    """
    Runs 'systemctl status' and parses the output for key information.
    """
    try:
        result = subprocess.run(
            ['sudo', 'systemctl', 'status', service_name],
            capture_output=True,
            text=True,
            check=False
        )
        output = result.stdout

        # --- Initialize port to a default value ---
        port_str = "N/A"

        # --- Parse for Port (if it exists) ---
        # This regex is more specific to the Gunicorn/Docker output.
        port_match = re.search(r"Listening at: http://[\d\.]+?:(\d+)", output)
        if not port_match:
            # Add a second check for filebrowser's different format
            port_match = re.search(r"Listening on \[::\]:(\d+)", output)

        if port_match:
            port_str = port_match.group(1)

        # --- Parse for Status ---
        active_line = re.search(r"Active:\s+(.*)", output) # Corrected typo here
        if not active_line:
            return service_name, "[red]Not Found[/red]", "N/A", port_str

        full_status_string = active_line.group(1).strip()
        main_status_match = re.match(r"(\w+).*", full_status_string)
        main_status = main_status_match.group(1) if main_status_match else "unknown"
        time_since_match = re.search(r"since .*;\s+(.*)", full_status_string)
        time_active = time_since_match.group(1).strip() if time_since_match else "N/A"

        # --- Apply Color Coding ---
        if "active (running)" in full_status_string:
            status_color = "[bold green]Active (Running)[/bold green]"
        elif "active (exited)" in full_status_string:
            status_color = "[bold yellow]Active (Exited)[/bold yellow]"
        elif "inactive" in full_status_string:
            status_color = "[bold yellow]Inactive[/bold yellow]"
        elif "failed" in full_status_string:
            status_color = "[bold red]Failed[/bold red]"
        else:
            status_color = f"[white]{main_status}[/white]"

        return service_name, status_color, time_active, port_str

    except FileNotFoundError:
        return service_name, "[bold red]Systemctl Not Found[/bold red]", "N/A", "N/A"
    except Exception as e:
        return service_name, f"[bold red]ERROR: {e}[/bold red]", "N/A", "N/A"


def main():
    """
    Main function to create and print the status table.
    """
    machine_name = socket.gethostname()
    console = Console()
    table = Table(show_header=True, header_style="bold magenta")
    table.add_column(machine_name, style="cyan", no_wrap=True)
    table.add_column("Status", justify="left")
    table.add_column("Time", justify="right")
    table.add_column("Port", justify="right", style="yellow") # Added Port column

    with console.status("[bold green]Querying services...[/bold green]"):
        for service in SERVICE_LIST:
            # Unpack the new port value
            name, status, time, port = get_service_status(service)
            # Add the port to the row
            table.add_row(name, status, time, port)

    console.print(table)


if __name__ == "__main__":
    main()

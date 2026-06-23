#!/home/al/miniconda3/envs/py/bin/python3
# -*- coding: utf-8 -*-
"""
Check which emulators exist and install missing ones.
"""

import os
import subprocess
from rich.console import Console
from rich.table import Table
from rich import box

console = Console()

# Emulator mapping: executable path -> package name
EMULATORS = {
    '/usr/bin/x64sc': 'vice',
    '/usr/bin/atari800': 'atari800',
    '/usr/bin/stella': 'stella',
    '/usr/bin/hatari': 'hatari',
    '/usr/bin/dosbox': 'dosbox',
    '/usr/bin/fceux': 'fceux',
    '/usr/bin/snes9x-gtk': 'snes9x-gtk',
    '/usr/bin/mupen64plus': 'mupen64plus-ui-console',
    '/usr/bin/desmume': 'desmume',
    '/usr/bin/visualboyadvance': 'visualboyadvance',
    '/usr/bin/osmose': 'osmose-emulator',
    '/usr/bin/gens': 'gens',
    '/usr/bin/mednafen': 'mednafen',
    '/usr/bin/gngeo': 'gngeo',
    '/usr/bin/mame': 'mame',
    '/usr/bin/ppsspp': 'ppsspp',
}

def check_emulators():
    """Check which emulators exist and which are missing."""
    existing = []
    missing = []
    
    for exe_path, package in EMULATORS.items():
        if os.path.exists(exe_path):
            existing.append((exe_path, package, "✓"))
        else:
            missing.append((exe_path, package, "✗"))
    
    return existing, missing

def display_status(existing, missing):
    """Display emulator status in a table."""
    table = Table(title="Emulator Status", box=box.ROUNDED)
    table.add_column("Status", style="bold", width=8)
    table.add_column("Executable", style="cyan")
    table.add_column("Package Name", style="yellow")
    
    for exe, pkg, status in existing:
        table.add_row(f"[green]{status}[/green]", exe, pkg)
    
    for exe, pkg, status in missing:
        table.add_row(f"[red]{status}[/red]", exe, pkg)
    
    console.print(table)
    console.print(f"\n[bold green]Installed:[/bold green] {len(existing)}")
    console.print(f"[bold red]Missing:[/bold red] {len(missing)}")

def install_missing(missing):
    """Install missing emulators."""
    if not missing:
        console.print("\n[bold green]All emulators are already installed![/bold green]")
        return
    
    console.print(f"\n[bold yellow]Found {len(missing)} missing emulators.[/bold yellow]")
    
    # Ask for confirmation
    response = input("\nDo you want to install them? (y/n): ").strip().lower()
    if response != 'y':
        console.print("[yellow]Installation cancelled.[/yellow]")
        return
    
    # Collect package names
    packages = [pkg for _, pkg, _ in missing]
    
    console.print(f"\n[bold cyan]Installing packages:[/bold cyan] {', '.join(packages)}")
    
    # Update package list first
    console.print("\n[bold]Updating package lists...[/bold]")
    try:
        subprocess.run(['sudo', 'apt', 'update'], check=True)
    except subprocess.CalledProcessError as e:
        console.print(f"[bold red]Error updating package lists:[/bold red] {e}")
        return
    
    # Install packages
    console.print("\n[bold]Installing emulators...[/bold]")
    try:
        cmd = ['sudo', 'apt', 'install', '-y'] + packages
        subprocess.run(cmd, check=True)
        console.print("\n[bold green]✓ Installation complete![/bold green]")
    except subprocess.CalledProcessError as e:
        console.print(f"\n[bold red]Error during installation:[/bold red] {e}")
        console.print("\n[yellow]Note:[/yellow] Some packages may not be available in your repositories.")
        console.print("You may need to install them manually or add additional repositories.")

def main():
    console.print("[bold cyan]Retro Gaming Emulator Installer[/bold cyan]\n")
    
    console.print("Checking installed emulators...\n")
    existing, missing = check_emulators()
    
    display_status(existing, missing)
    
    if missing:
        install_missing(missing)
        
        # Recheck after installation
        console.print("\n[bold]Rechecking status...[/bold]\n")
        existing, missing = check_emulators()
        display_status(existing, missing)

if __name__ == "__main__":
    main()

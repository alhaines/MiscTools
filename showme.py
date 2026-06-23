#!/home/al/miniconda3/envs/py/bin/python3
# -*- coding: utf-8 -*-
#
# filename:   /home/al/py/showmev25.py
#
# Copyright 2025 AL Haines
#
# v25.0: Restores the full suite of command-line arguments (last,
#        fulltext, etc.) while using the simple, non-paginated rich
#        table for dashboard-safe display.

import sys
import argparse
import os

try:
    from MySql import MySQL
    from rich.console import Console
    from rich.table import Table
    from rich.panel import Panel
    from rich.text import Text
except ImportError as e:
    print(f"FATAL: Required library missing: {e}", file=sys.stderr)
    sys.exit(1)

def get_console_width() -> int:
    custom_width_str = os.environ.get('AL_TERMINAL_WIDTH')
    if custom_width_str:
        try:
            return int(custom_width_str) - 2
        except (ValueError, TypeError):
            pass
    try:
        return os.get_terminal_size().columns
    except OSError:
        pass
    return 80

console = Console(width=get_console_width())

def _decode_row(row: dict) -> dict:
    if not row: return {}
    clean_row = {}
    for key, value in row.items():
        if isinstance(value, bytes):
            clean_row[key] = value.decode('latin1', errors='replace')
        else:
            clean_row[key] = str(value) if value is not None else ""
    return clean_row

def print_formatted_record(record: dict):
    clean_record = _decode_row(record)
    if not clean_record:
        console.print("[bold red]Record not found.[/bold red]")
        return
    table = Table.grid(expand=True, padding=(0, 1))
    table.add_column(style="cyan", justify="right", width=15)
    table.add_column(style="white")
    record_id = clean_record.get('id', 'N/A')
    record_title = clean_record.get('title', 'N/A')
    panel_title = f"[bold yellow]ID: {record_id} | {record_title}[/bold yellow]"
    for key, value in clean_record.items():
        table.add_row(f"[bold cyan]{key.upper()}:[/bold cyan]", value)
    console.print(Panel(table, title=panel_title, border_style="blue", expand=True))

class ShowMeApp:
    def __init__(self, db_name):
        self.db = MySQL(database=db_name)
        self.db_name = db_name

    def get_last_record(self, table_name):
        results = self.db.get_data(f"SELECT * FROM `{table_name}` ORDER BY id DESC LIMIT 1")
        if results:
            print_formatted_record(results[0])
        else:
            console.print(f"[red]No records found.[/red]")

    def display_table(self, table_name):
        all_data = self.db.get_data(f"SELECT * FROM `{table_name}` ORDER BY id ASC")
        if not all_data:
            console.print(f"[yellow]Table '{table_name}' is empty.[/yellow]")
            return
        clean_data = [_decode_row(row) for row in all_data]
        column_names = list(clean_data[0].keys())
        display_table = Table(title=f"Table: {table_name} ({len(clean_data)} rows)", border_style="green")
        for col_name in column_names:
            display_table.add_column(col_name)
        for row in clean_data:
            display_table.add_row(*[row.get(col_name, '') for col_name in column_names])
        console.print(display_table)

    def view_full_text(self, table_name, record_id, column_name):
        query = f"SELECT `{column_name}` FROM `{table_name}` WHERE id = %s"
        results = self.db.get_data(query, (int(record_id),))
        if results:
            clean_record = _decode_row(results[0])
            content = clean_record.get(column_name, "[red]Not found.[/red]")
            console.print(Panel(Text(content), title=f"[bold yellow]Full text for {table_name}.{column_name} (ID: {record_id})[/bold yellow]"))
        else:
            console.print(f"[red]No record found with ID: {record_id}[/red]")
            
    def list_tables(self):
        tables = self.db.get_data("SHOW TABLES")
        if tables:
            clean_tables = [_decode_row(t) for t in tables]
            table_list = [list(t.values())[0] for t in clean_tables]
            console.print(Panel("    " + "\n    ".join(f"- {name}" for name in table_list), title="[bold yellow]Tables Found[/bold yellow]"))
        else:
            console.print("[red]No tables found.[/red]")
            
    def get_last_id(self, table_name):
        query = f"SELECT MAX(id) as max_id FROM `{table_name}`"
        results = self.db.get_data(query)
        if results and results[0]['max_id'] is not None:
            console.print(Panel(f"The highest ID is [bold green]{results[0]['max_id']}[/bold green]", title=f"[yellow]Last ID in {table_name}[/yellow]"))
        else:
            console.print(f"[red]Could not determine last ID for table '{table_name}'.[/red]")
            
    def list_fields(self, table_name):
        schema = self.db.get_data(f"DESCRIBE `{table_name}`")
        if not schema:
            console.print(f"[red]Could not describe table '{table_name}'.[/red]")
            return
        table = Table(title=f"Fields for {table_name}", border_style="green", show_lines=True)
        headers = list(schema[0].keys())
        for header in headers:
            table.add_column(header, style="cyan")
        for row in schema:
            table.add_row(*[str(val) for val in row.values()])
        console.print(table)

def main():
    parser = argparse.ArgumentParser(description="A context-aware CLI for viewing MySQL databases.")
    parser.add_argument("database")
    subparsers = parser.add_subparsers(dest='action', required=True, help="The action to perform.")
    
    # --- Correct, Full Argument Parser Definitions ---
    p_last = subparsers.add_parser('last')
    p_last.add_argument("table")
    
    p_display = subparsers.add_parser('display')
    p_display.add_argument("table")
    
    p_list = subparsers.add_parser('list')
    
    p_lastid = subparsers.add_parser('lastid')
    p_lastid.add_argument("table")
    
    p_fields = subparsers.add_parser('fields')
    p_fields.add_argument("table")
    
    p_fulltext = subparsers.add_parser('fulltext')
    p_fulltext.add_argument("table")
    p_fulltext.add_argument("id")
    p_fulltext.add_argument("column")
    
    args = parser.parse_args()
    app = ShowMeApp(args.database)
    
    # --- Correct, Full Dispatch Logic ---
    if args.action == 'last':
        app.get_last_record(args.table)
    elif args.action == 'display':
        app.display_table(args.table)
    elif args.action == 'list':
        app.list_tables()
    elif args.action == 'lastid':
        app.get_last_id(args.table)
    elif args.action == 'fields':
        app.list_fields(args.table)
    elif args.action == 'fulltext':
        app.view_full_text(args.table, args.id, args.column)

if __name__ == "__main__":
    main()

#!/home/al/miniconda3/envs/py/bin/python3
# -*- coding: utf-8 -*-
#
# filename:   backup_functions.py
#
# Copyright 2025 AL Haines
#
# DEFINITIVE FIX 10.0: Reinstates the user's CRITICAL safety rule as the
# absolute first check. The script will NOT process any file modified before
# today. This is combined with the manifest for handling files from today.

import os
import shutil
import sys
from datetime import datetime

try:
    from MySql import MySQL
except ImportError:
    print("FATAL: Could not import MySql.py.", file=sys.stderr)
    sys.exit(1)

# --- Configuration ---
DESTINATION_ROOT = "/home/al/MyFiles/BO"
MANIFEST_TABLE = "backup_manifest"
BACKUP_LOG_TABLE = "CP_journal"
IGNORE_PATTERNS = [ "/__pycache__/", "/var/www/html/nextcloud/data", "/.git/" ]

def _log_to_cp_journal(db, message: str):
    """(Internal) Logs a message directly to the CP_journal table."""
    timestamp = datetime.now().strftime("%Y%m%d%H%M%S%f")
    query = f"INSERT INTO {BACKUP_LOG_TABLE} (title, note) VALUES (%s, %s)"
    try:
        db.put_data(query, (timestamp, message))
    except Exception as e:
        print(f"ERROR: Database error during logging: {e}", file=sys.stderr)

def load_manifest(db):
    """Loads the backup manifest from the database."""
    print("Loading backup manifest from database...", file=sys.stderr)
    query = f"SELECT source_path, last_backed_up_size, last_backed_up_mtime FROM {MANIFEST_TABLE}"
    manifest_data = db.get_data(query)
    if manifest_data is None:
        print(f"FATAL: Could not query manifest table.", file=sys.stderr)
        sys.exit(1)
    return {item['source_path']: item for item in manifest_data}

def update_manifest(db, source_path, size, mtime):
    """Inserts or updates a record in the manifest table."""
    now_ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    query = f"""
        INSERT INTO {MANIFEST_TABLE} (source_path, last_backed_up_size, last_backed_up_mtime, last_backup_timestamp)
        VALUES (%s, %s, %s, %s) ON DUPLICATE KEY UPDATE
        last_backed_up_size = VALUES(last_backed_up_size), last_backed_up_mtime = VALUES(last_backed_up_mtime), last_backup_timestamp = VALUES(last_backup_timestamp);
    """
    db.put_data(query, (source_path, size, mtime, now_ts))

def perform_backup():
    """The main backup function with the 'today' safety filter reinstated."""
    print("--- Starting SAFE backup scan (HARD 'TODAY' FILTER ENABLED)... ---", file=sys.stderr)

    start_of_today = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
    db = MySQL()
    manifest = load_manifest(db)
    query = "SELECT path FROM update_paths WHERE enabled = 1"
    source_dirs_data = db.get_data(query)

    if not source_dirs_data:
        return

    source_paths = [item['path'] for item in source_dirs_data]
    files_copied = 0
    files_scanned = 0
    files_ignored_pattern = 0
    files_ignored_date = 0

    for path in source_paths:
        if not os.path.isdir(path):
            continue

        for dirpath, _, filenames in os.walk(path):
            for filename in filenames:
                files_scanned += 1
                source_file = os.path.join(dirpath, filename)

                try:
                    # --- SAFETY RULE #1: IGNORE PATTERNS ---
                    if any(pattern in source_file for pattern in IGNORE_PATTERNS):
                        files_ignored_pattern += 1
                        continue

                    source_mtime_float = os.path.getmtime(source_file)

                    # --- SAFETY RULE #2: YOUR 'TODAY' FILTER ---
                    # This is the most important check. If a file is old, we do nothing.
                    if datetime.fromtimestamp(source_mtime_float) < start_of_today:
                        files_ignored_date += 1
                        continue

                    # --- ONLY if a file is from today, we proceed to the manifest logic ---
                    current_size = os.path.getsize(source_file)
                    current_mtime = int(source_mtime_float)
                    manifest_entry = manifest.get(source_file)

                    should_copy = False
                    if not manifest_entry:
                        should_copy = True
                    else:
                        manifest_size = int(manifest_entry['last_backed_up_size'])
                        manifest_mtime = int(manifest_entry['last_backed_up_mtime'])
                        if current_size != manifest_size or current_mtime > manifest_mtime:
                            should_copy = True

                    if should_copy:
                        dest_file = os.path.join(DESTINATION_ROOT, source_file.lstrip('/'))
                        dest_dir = os.path.dirname(dest_file)
                        os.makedirs(dest_dir, exist_ok=True)

                        shutil.copy2(source_file, dest_file)
                        update_manifest(db, source_file, current_size, current_mtime)

                        log_message = f"Copied {source_file} to Vault"
                        _log_to_cp_journal(db, log_message)
                        files_copied += 1
                except Exception as e:
                    print(f"ERROR: Failed to process file {source_file}: {e}", file=sys.stderr)

    print(f"--- Backup scan finished. Scanned: {files_scanned} | Ignored by Pattern: {files_ignored_pattern} | Ignored by Date: {files_ignored_date} | Copied: {files_copied} ---", file=sys.stderr)

if __name__ == '__main__':
    perform_backup()

#
# filename:   /home/al/projects/config.py
#
"""
Configuration for mainmenu application and related services.
"""

import os
import pymysql

# Database credentials
DB_HOST = 'localhost'
DB_USER = 'root'
DB_PASSWORD = 'password'

# Database configurations for different services
# Main menu database (users, siteslinks, contacts, etc.)
db_mainmenu = {
    'host': DB_HOST,
    'user': DB_USER,
    'password': DB_PASSWORD,
    'database': 'als'
}

# Media library database (videos, audio, etc.)
db_media = {
    'host': DB_HOST,
    'user': DB_USER,
    'password': DB_PASSWORD,
    'database': 'als'
}

# Games/ROM database
db_games = {
    'host': DB_HOST,
    'user': DB_USER,
    'password': DB_PASSWORD,
    'database': 'games'
}
# Blog database
db_blog = {
    'host': DB_HOST,
    'user': DB_USER,
    'password': DB_PASSWORD,
    'database': 'als'
}
mysql_config  = db_media

# Path to external hard drive
external_hard_drive_path = '/home/al/Media'

# Path to external hard drive
external_hard_drive_path2 = '/home/al/Movies'

# Path to 4 TB external hard drive
Movies = '/home/al/Movies'

# Path to 10 TB external hard drive
Media = '/home/al/Media'

# Path to new videos
VideoDownloader = '/home/al/Downloads/VideoDownloader'

# Dynamic table_list function - loads from table_data instead of hard-coding
def get_table_list():
    """
    Retrieve table list from table_data database table.
    Returns list of tuples: [(path, table_name), ...]
    """
    try:
        conn = pymysql.connect(**mysql_config, cursorclass=pymysql.cursors.DictCursor)
        with conn.cursor() as cursor:
            cursor.execute("SELECT path, `table` FROM table_data ORDER BY level, title")
            results = cursor.fetchall()
            return [(row['path'], row['table']) for row in results]
    except Exception as e:
        print(f"Error loading table_list from database: {e}")
        return []
    finally:
        if 'conn' in locals():
            conn.close()

def get_table_titles():
    """
    Retrieve mapping of table names to display titles from table_data.
    Returns dict: {table_name: title, ...}
    """
    try:
        conn = pymysql.connect(**mysql_config, cursorclass=pymysql.cursors.DictCursor)
        with conn.cursor() as cursor:
            cursor.execute("SELECT `table`, title FROM table_data")
            results = cursor.fetchall()
            return {row['table']: row['title'] for row in results}
    except Exception as e:
        print(f"Error loading table titles from database: {e}")
        return {}
    finally:
        if 'conn' in locals():
            conn.close()

def get_video_tables():
    """
    Retrieve list of video table names from table_data.
    Returns list: [table_name, ...]
    """
    try:
        conn = pymysql.connect(**mysql_config, cursorclass=pymysql.cursors.DictCursor)
        with conn.cursor() as cursor:
            cursor.execute("SELECT `table` FROM table_data WHERE media_type = 'video'")
            results = cursor.fetchall()
            return [row['table'] for row in results]
    except Exception as e:
        print(f"Error loading video tables from database: {e}")
        return []
    finally:
        if 'conn' in locals():
            conn.close()

def get_audio_tables():
    """
    Retrieve list of audio table names from table_data.
    Returns list: [table_name, ...]
    """
    try:
        conn = pymysql.connect(**mysql_config, cursorclass=pymysql.cursors.DictCursor)
        with conn.cursor() as cursor:
            cursor.execute("SELECT `table` FROM table_data WHERE media_type = 'audio'")
            results = cursor.fetchall()
            return [row['table'] for row in results]
    except Exception as e:
        print(f"Error loading audio tables from database: {e}")
        return []
    finally:
        if 'conn' in locals():
            conn.close()

# Load table_list dynamically from database
table_list = get_table_list()
table_titles = get_table_titles()
video_tables = get_video_tables()
audio_tables = get_audio_tables()


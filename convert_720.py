#!/home/al/miniconda3/envs/py/bin/python3
# -*- coding: utf-8 -*-
#
#  Copyright 2023 AL Haines <alfredhaines@gmail.com>
#
#  filename /home/al/py/convert_720.py
#
#  This program is free software; you can redistribute it and/or modify
#  it under the terms of the GNU General Public License as published by
#  the Free Software Foundation; either version 2 of the License, or
#  (at your option) any later version.
#
#  This program is distributed in the hope that it will be useful,
#  but WITHOUT ANY WARRANTY; without even the implied warranty of
#  MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#  GNU General Public License for more details.
# ffmpeg -i '/home/al/Media/TV_Shows/Terra_Nova/Terra_Nova_2011_S01/Terra_Nova_2011_S01E03_What Remains.mp4' -c:v libx24 -preset veryfast -crf 23 -c:a aac -b:a 192k -ac 2 -movflags +faststart '/home/al/Media/TV_Shows/Terra_Nova/Terra_Nova/Terra_Nova_2011_S01/Terra_Nova_E03_FINAL.mp4'
#  filename: /home/al/py/convert_files.py

import os
import sys
import subprocess
from datetime import datetime

def convert_files(input_folder):
    """
    Converts video files to 720p HEVC and saves them to the '0_to_be_tested' staging area.
    """
    base_test_dir = "/home/al/Media/TV_Shows/0_to_be_tested"
    valid_exts = (".mkv", ".avi", ".mov", ".wmv", ".flv", ".mp4")

    for filename in os.listdir(input_folder):
        if filename.lower().endswith(valid_exts):
            # Extract title (filename without extension)
            title = os.path.splitext(filename)[0]

            # Define and create the specific output folder for this title
            output_folder = os.path.join(base_test_dir, title)
            os.makedirs(output_folder, exist_ok=True)

            input_file = os.path.join(input_folder, filename)
            output_file = os.path.join(output_folder, f"{title}_720p_HEVC.mp4")

            # --- 720p HEVC COMMAND ---
            ffmpeg_command = [
                "ffmpeg",
                "-i", input_file,
                "-vf", "scale=-2:720",
                "-c:v", "libx265",
                "-crf", "28",
                "-preset", "medium",
                "-c:a", "aac",
                "-b:a", "128k",
                "-ac", "2",
                "-tag:v", "hvc1",
                "-movflags", "+faststart",
                "-y", # Overwrite if exists
                output_file,
            ]

            try:
                print(f"{datetime.now():%Y-%m-%d %I:%M:%S} - Processing: {title}")
                print(f"Outputting to: {output_folder}")
                subprocess.run(ffmpeg_command, check=True)
            except subprocess.CalledProcessError as e:
                print(f"FFmpeg error on {filename}: {e}")
            except Exception as e:
                print(f"General error on {filename}: {e}")

if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("Usage: convert_files.py <input_folder>")
        sys.exit(1)

    target_dir = sys.argv[1]
    if not os.path.isdir(target_dir):
        print(f"Error: {target_dir} is not a valid directory.")
        sys.exit(1)

    convert_files(target_dir)
    print("\nProcessing complete! Check /home/al/Media/TV_Shows/0_to_be_tested/ for your files.")

#!/home/al/miniconda3/envs/py/bin/python3
# -*- coding: utf-8 -*-
#
# filename:   /home/al/py/test_ov_functions.py
#
# Copyright 2026 AL Haines
# Coding by AI Collaborator
#
# Description: A Python and Rich-based boot menu shell script,
# select iso from listing than edit grub with selection

import io
import subprocess
import sys
import unittest
from contextlib import redirect_stdout
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parent))

import OV


# ---------------------------------------------------------------------------
# Helper used by the tests below.
#
# This little mixin captures printed text from OV methods so we can verify
# that the functions are generating the expected HTML without having to open a
# browser. It is a simple pattern: run the function, collect what it printed,
# and compare that output to the expected HTML fragment.
# ---------------------------------------------------------------------------
class CaptureMixin:
    def capture_stdout(self, func, *args, **kwargs):
        buf = io.StringIO()
        with redirect_stdout(buf):
            result = func(*args, **kwargs)
        return result, buf.getvalue()


# ---------------------------------------------------------------------------
# TestOVHelpers
#
# This is the main test class for the OV.py module. Each method checks one
# group of related functions in a simple, easy-to-read way.
#
# The idea is intentionally straightforward:
#   1. set up the data,
#   2. call the OV function,
#   3. assert the return value or printed HTML matches what we expect.
#
# This keeps the test file readable for someone learning the code, instead of
# hiding everything inside a complicated fixture system.
# ---------------------------------------------------------------------------
class TestOVHelpers(unittest.TestCase, CaptureMixin):

    # -------------------------------------------------------------------
    # Disk usage parsing test.
    #
    # This verifies that OV.get_disk_usage_data() can read the output of
    # "df -T" and turn it into a clean list of dictionaries. The test uses a
    # mocked subprocess result so we do not need to touch the real system disk.
    # -------------------------------------------------------------------
    def test_get_disk_usage_data_parses_df_output(self):
        stdout = """Filesystem     Type 1K-blocks Used Available Use% Mounted on
/dev/sda1     ext4  100000  50000  40000  50% /
//server/share cifs 200000 10000 190000 5% /mnt/share
"""

        with patch.object(subprocess, 'run', return_value=SimpleNamespace(stdout=stdout, stderr='', returncode=0)):
            rows = OV.get_disk_usage_data()

        self.assertEqual(rows, [
            {
                'device': '/dev/sda1',
                'type': 'ext4',
                'mountpoint': '/',
                'total_kb': 100000,
                'used_kb': 50000,
                'free_kb': 40000,
            },
            {
                'device': '//server/share',
                'type': 'cifs',
                'mountpoint': '/mnt/share',
                'total_kb': 200000,
                'used_kb': 10000,
                'free_kb': 190000,
            },
        ])

    # -------------------------------------------------------------------
    # Mount mode test.
    #
    # /proc/mounts is the system source for mount options. We check that the
    # function correctly returns 'rw', 'ro', or 'unknown' based on the mount
    # entry for a given path.
    # -------------------------------------------------------------------
    def test_get_mount_access_mode_reads_proc_mounts(self):
        mount_data = """rootfs / rootfs rw 0 0
/dev/sda1 / ext4 rw,relatime 0 0
//server/share /mnt/share cifs rw,vers=3.0 0 0
"""

        def fake_open(path, *args, **kwargs):
            if path == '/proc/mounts':
                return io.StringIO(mount_data)
            raise FileNotFoundError(path)

        with patch('builtins.open', side_effect=fake_open):
            self.assertEqual(OV.get_mount_access_mode('/'), 'rw')
            self.assertEqual(OV.get_mount_access_mode('/mnt/share'), 'rw')
            self.assertEqual(OV.get_mount_access_mode('/missing'), 'unknown')

    # -------------------------------------------------------------------
    # Classification and status tests.
    #
    # These functions are the decision-makers for the report. They decide if a
    # device is a local disk, external disk, or mounted network share, and what
    # kind of status message should be shown for it.
    # -------------------------------------------------------------------
    def test_classify_and_status_helpers(self):
        entry_local = {'device': '/dev/sda1', 'type': 'ext4', 'mountpoint': '/'}
        entry_share = {'device': '//server/share', 'type': 'cifs', 'mountpoint': '/mnt/share'}

        self.assertEqual(OV.classify_entry(entry_local), 'Internal Drives')
        self.assertEqual(OV.classify_entry(entry_share), 'Mounted Shares')
        self.assertEqual(OV.get_entry_endpoint(entry_share), '//server/share')
        self.assertEqual(OV.get_health_status(95), '[bold red]CRIT[/bold red]')
        self.assertEqual(OV.get_health_status(75), '[yellow]WARN[/yellow]')
        self.assertEqual(OV.get_health_status(40), '[green]OK[/green]')
        self.assertEqual(OV.format_state_code('local'), '[dim]l[/dim]')
        self.assertEqual(OV.format_state_code('reachable'), '[green]r[/green]')
        self.assertEqual(OV.format_gb_short(1.25), '1.2G')
        self.assertEqual(OV.format_free_value(2.5, 90), '[green]2.5G[/green]')
        self.assertEqual(OV.format_free_value(2.5, 15), '[yellow]2.5G[/yellow]')
        self.assertEqual(OV.format_free_value(0.5, 3), '[bold red]0.5G[/bold red]')

    # -------------------------------------------------------------------
    # Share reachability test.
    #
    # For network shares, the important question is whether the mount is alive.
    # This test mocks the subprocess call and verifies the result is treated as
    # reachable when the stat check succeeds.
    # -------------------------------------------------------------------
    def test_get_share_status_uses_mount_checks(self):
        with patch.object(subprocess, 'run', return_value=SimpleNamespace(returncode=0, stdout='', stderr='')):
            entry = {'device': '//server/share', 'type': 'cifs', 'mountpoint': '/mnt/share'}
            self.assertEqual(OV.get_share_status(entry), 'reachable')

    # -------------------------------------------------------------------
    # Rich table rendering test.
    #
    # This checks the final presentation layer for the disk report. It confirms
    # the table has the expected title and column headings, which helps ensure
    # the report stays readable for the user.
    # -------------------------------------------------------------------
    def test_build_extended_table_renders_expected_columns(self):
        groups = {
            'Internal Drives': [{
                'hostname': 'host01',
                'device': '/dev/sda1',
                'mountpoint': '/',
                'type': 'ext4',
                'free_kb': 50000,
                'free_pct': 50.0,
                'health_status': '[green]OK[/green]',
            }],
            'External Drives': [],
            'Mounted Shares': [],
        }

        table = OV.build_extended_table(groups, 'host01', '2025-01-01 12:00:00')

        self.assertEqual(table.title, 'Extended Disk Info (2025-01-01 12:00:00)')
        self.assertEqual(
            [column.header for column in table.columns],
            ['host01', 'Drive', 'Mountpoint', 'FS Type', 'Free %', 'Health'],
        )

    # -------------------------------------------------------------------
    # HTML output methods.
    #
    # These are the classic OV methods that print HTML fragments directly to the
    # terminal. We test them as a set because they all follow the same pattern:
    # call the method, capture printed output, and assert key HTML markers are
    # present in that output.
    # -------------------------------------------------------------------
    def test_ov_output_helpers(self):
        ov = OV.OV()

        cases = [
            (lambda: ov.E('Hello world'), 'Hello world'),
            (lambda: ov.Image('/img/logo.png', width=200, height=80, border=1, title='Logo'), '<IMG SRC="/img/logo.png"'),
            (lambda: ov.AStart('/home', class_name='nav'), '<A HREF="/home"'),
            (lambda: ov.Bold('Bold text', class_name='warn'), '<B'),
            (lambda: ov.Br(2), '<BR>'),
            (lambda: ov.Div(id_name='main', style='padding:10px'), '<DIV'),
            (lambda: ov.Head(), '<!DOCTYPE html><html><Head>'),
            (lambda: ov.Body(action='onload="ready()"'), '<BODY'),
            (lambda: ov.Style('/static/site.css'), '<link href="/static/site.css"'),
            (lambda: ov.Refresh('/next', delay=2), 'REFRESH'),
            (lambda: ov.P('Paragraph', class_name='lead'), '<P'),
            (lambda: ov.Pre('hello', width=40, class_name='code'), '<PRE'),
            (lambda: ov.Q('Quote', class_name='note'), '<Q'),
            (lambda: ov.S('struck', class_name='old'), '<S'),
            (lambda: ov.Samp('x = 1', class_name='code'), '<SAMP'),
            (lambda: ov.Span('Badge', style='color:red', class_name='tag'), '<SPAN'),
            (lambda: ov.H('Heading', class_name='2'), '<H2'),
            (lambda: ov.TblStart(border='1', width='100%'), '<TABLE'),
            (lambda: ov.TblStartLine(align='left'), '<TR'),
            (lambda: ov.TblEntete('Name'), '<TH'),
            (lambda: ov.TblStartCell(width='25%', align='left'), '<TD'),
            (lambda: ov.TblCell('Cell', align='center'), '<TD'),
        ]

        for action, expected in cases:
            _, output = self.capture_stdout(action)
            self.assertIn(expected, output)

    # -------------------------------------------------------------------
    # Closing tags and script tests.
    #
    # These are the "end of block" helpers. They are simple, but they matter:
    # without them, the generated HTML page would not close properly.
    # -------------------------------------------------------------------
    def test_ov_closing_tags_and_script_helpers(self):
        ov = OV.OV()

        _, output = self.capture_stdout(lambda: ov.AEnd())
        self.assertIn('</A>', output)

        _, output = self.capture_stdout(lambda: ov.DivEnd())
        self.assertIn('</DIV>', output)

        _, output = self.capture_stdout(lambda: ov.HeadEnd())
        self.assertIn('</Head>', output)

        _, output = self.capture_stdout(lambda: ov.BodyEnd())
        self.assertIn('</BODY>', output)

        _, output = self.capture_stdout(lambda: ov.TblEnd())
        self.assertIn('</TABLE>', output)

        _, output = self.capture_stdout(lambda: ov.TblEndLine())
        self.assertIn('</TR>', output)

        _, output = self.capture_stdout(lambda: ov.TblEndCell())
        self.assertIn('</TD>', output)

        _, output = self.capture_stdout(lambda: ov.ScriptS('text/javascript', 'JavaScript', '/js/app.js'))
        self.assertIn('<SCRIPT LANGUAGE="JavaScript" TYPE="text/javascript" src="/js/app.js">', output)

        _, output = self.capture_stdout(lambda: ov.ScriptEnd())
        self.assertEqual(output, '')

    # -------------------------------------------------------------------
    # Global helper functions.
    #
    # These functions do not live inside the OV class. They produce strings or
    # print HTML snippets that can be dropped into larger pages. They are meant
    # to be used as quick utility helpers when the app needs a little more than
    # plain text.
    # -------------------------------------------------------------------
    def test_ov_global_helpers_return_strings_and_markup(self):
        self.assertIn('href="/docs"', OV.ovl('/docs', "'Doc tooltip'", 'Docs'))
        self.assertIn('<br />', OV.make_bar('/help[,]Help text[,]Docs'))
        self.assertEqual('<li> Demo</li>', OV.li('Demo'))

        _, output = self.capture_stdout(OV.prpix, '/img/test.png', 100, 50)
        self.assertIn('<img src="/img/test.png" width="100" height="50">', output)

        _, output = self.capture_stdout(OV.pruff, 'Status', 3)
        self.assertIn('<p><font color="000000" size="3">Status</font></p>', output)

        self.assertEqual(
            OV.pr_html({'server': 'web01'}, as_return=True),
            "<pre>{&#x27;server&#x27;: &#x27;web01&#x27;}</pre>",
        )
        self.assertEqual(OV.Pad('-', 4), '----')
        self.assertEqual(OV.getCSVValue('a,"b,c",d'), ['a', 'b,c', 'd'])

    # -------------------------------------------------------------------
    # CSV and HTML escaping checks.
    #
    # These tests make sure values are parsed correctly and special characters
    # are converted safely when printing HTML. This is important for avoiding
    # broken output in a browser.
    # -------------------------------------------------------------------
    def test_ov_csv_and_html_escaping_round_trip(self):
        self.assertEqual(OV.getCSVValue('"quoted","value"'), ['quoted', 'value'])
        escaped = OV.pr_html('5 < 6 & 7', as_return=True)
        self.assertIn('5 &lt; 6 &amp; 7', escaped)


if __name__ == '__main__':
    unittest.main()


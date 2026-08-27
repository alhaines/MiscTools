# OV.py

OV.py is a lightweight HTML and utility helper module designed to make it easy to generate simple HTML markup from Python, especially for older web-style apps and dashboard pages.

It includes:

- HTML output helpers such as `OV.E()`, `OV.Div()`, `OV.TblStart()`, and `OV.Image()`
- Text formatting helpers like `Bold()`, `Span()`, `P()`, `Pre()`, and `H()`
- OverLib-style tooltip helpers such as `ovl()` and `make_bar()`
- Support functions like `li()`, `pr_html()`, `Pad()`, and `getCSVValue()`
- Disk/report helper functions used by monitoring tools, such as `get_disk_usage_data()`, `classify_entry()`, and `build_extended_table()`

Important note for new users:

- Most methods in the `OV` class print HTML directly to stdout.
- A few helper functions return strings that you can embed in templates or pages.
- This module is best when you want quick HTML fragments without a full templating framework.

---

## Quick start

```python
from OV import OV

ov = OV()
ov.Head()
ov.Body()
ov.Div(id_name="content")
ov.P("Hello from OV.py")
ov.AStart("https://example.com", class_name="btn")
ov.Bold("Visit the site")
ov.AEnd()
ov.DivEnd()
ov.BodyEnd()
ov.HeadEnd()
```

This prints a basic HTML page outline.

---

## Function reference

### Core HTML helpers

+----------------------+-----------------------------------------------------+-----------------------------------------------------------+
| Function             | Purpose                                             | Example                                                   |
+======================+=====================================================+===========================================================+
| `OV.E(text)`        | Prints plain text                                   | `OV.E("Welcome!")`                                       |
| `OV.Image(...)`     | Outputs an `<img>` tag                              | `OV.Image("/images/logo.png", width=200, height=80)`    |
| `OV.AStart(...)`    | Starts a link tag                                   | `OV.AStart("/home", class_name="nav-link")`            |
| `OV.AEnd()`         | Closes an anchor tag                                | `OV.AEnd()`                                               |
| `OV.Bold(...)`      | Wraps text in `<b>`                                 | `OV.Bold("Important", class_name="warn")`              |
| `OV.Br(nbr)`        | Prints line breaks                                  | `OV.Br(2)`                                               |
| `OV.Div(...)`       | Starts a `<div>`                                    | `OV.Div(id_name="card", style="padding:10px")`        |
| `OV.DivEnd()`       | Ends a `<div>`                                      | `OV.DivEnd()`                                            |
| `OV.Head()`         | Starts an HTML document head                        | `OV.Head()`                                              |
| `OV.HeadEnd()`      | Closes the document head                            | `OV.HeadEnd()`                                           |
| `OV.Body(...)`      | Starts the page body                                | `OV.Body(action="onload=init()")`                       |
| `OV.BodyEnd()`      | Closes the body                                     | `OV.BodyEnd()`                                           |
| `OV.Style(url)`     | Adds a CSS link                                     | `OV.Style("/static/site.css")`                          |
| `OV.Refresh(href)`  | Adds a meta refresh redirect                        | `OV.Refresh("/login", delay=2)`                          |
| `OV.P(...)`         | Adds a paragraph                                     | `OV.P("Hello world", class_name="lead")`              |
| `OV.Pre(...)`       | Adds a preformatted block                            | `OV.Pre("name=value\nkey=value", width=80)`             |
| `OV.Q(...)`         | Adds a short quote                                  | `OV.Q("Keep going.")`                                   |
| `OV.S(...)`         | Strikethrough text                                  | `OV.S("obsolete")`                                      |
| `OV.Samp(...)`      | Sample code output                                  | `OV.Samp("print('hello')")`                             |
| `OV.Span(...)`      | Wraps text in a `<span>`                            | `OV.Span("Badge", class_name="tag")`                  |
| `OV.H(...)`         | Generates H1-H6 heading                             | `OV.H("Dashboard", class_name="2")`                   |
+----------------------+-----------------------------------------------------+-----------------------------------------------------------+

### Table helpers

+-------------------------------+-------------------------------------------------------------+---------------------------------------------------------------+
| Function                      | Purpose                                                     | Example                                                       |
+===============================+=============================================================+===============================================================+
| `OV.TblStart(...)`            | Opens a table with sizing and styling options               | `OV.TblStart(border="1", width="100%", class_name="data")` |
| `OV.TblEnd()`                 | Closes the table                                            | `OV.TblEnd()`                                                 |
| `OV.TblStartLine(...)`        | Opens a table row                                           | `OV.TblStartLine(align="left", bg="#f0f0f0")`             |
| `OV.TblEndLine()`             | Closes the row                                              | `OV.TblEndLine()`                                             |
| `OV.TblEntete(content, ...)`  | Creates a table header cell                                 | `OV.TblEntete("Name")`                                       |
| `OV.TblStartCell(...)`        | Opens a cell                                               | `OV.TblStartCell(width="25%", align="left")`               |
| `OV.TblEndCell()`             | Closes a cell                                              | `OV.TblEndCell()`                                             |
| `OV.TblCell(content, ...)`    | Creates a full cell with content                            | `OV.TblCell("Alice", align="center")`                      |
+-------------------------------+-------------------------------------------------------------+---------------------------------------------------------------+

### Utility and string helpers

+----------------------------+-----------------------------------------------+-----------------------------------------------------------+
| Function                   | Purpose                                       | Example                                                   |
+============================+===============================================+===========================================================+
| `ovl(a, b, c)`            | Generates an OverLib tooltip link             | `ovl("/docs", "'Docs tooltip'", "Docs")`              |
| `make_bar(str_val)`       | Wraps a link in a tooltip + break             | `make_bar("/help[,]Help text[,]Help")`                  |
| `li(a)`                   | Creates a list item                           | `li("First item")`                                      |
| `prpix(img, w, h)`        | Renders an image block                       | `prpix("/img/a.png", 200, 100)`                         |
| `pruff(txt, size)`        | Renders text with a font size                | `pruff("Status", 3)`                                    |
| `pr_html(a, as_return)`   | Escapes content and prints a `<pre>` block   | `pr_html({"name": "Ava"}, as_return=True)`              |
| `Pad(string, pad)`        | Repeats a string a fixed number of times     | `Pad("-", 10)`                                          |
| `getCSVValue(string)`     | Parses a CSV-like value list                 | `getCSVValue('a,"b,c",d')`                              |
+----------------------------+-----------------------------------------------+-----------------------------------------------------------+

### Disk and monitoring helpers

+---------------------------------------------+-----------------------------------------------------------+---------------------------------------------------------------+
| Function                                    | Purpose                                                   | Example                                                       |
+=============================================+===========================================================+===============================================================+
| `get_disk_usage_data()`                     | Runs `df -T` and returns structured mount data            | `rows = get_disk_usage_data()`                                 |
| `get_mount_access_mode(mountpoint)`        | Reads `/proc/mounts` and reports `ro`/`rw` status        | `mode = get_mount_access_mode('/mnt/share')`                 |
| `classify_entry(entry)`                     | Groups entries as internal, external, or mounted share    | `group = classify_entry(entry)`                                |
| `get_entry_endpoint(entry)`                 | Returns the device or share endpoint                      | `endpoint = get_entry_endpoint(entry)`                        |
| `get_share_status(entry)`                   | Checks if a mounted share is reachable                    | `status = get_share_status(entry)`                            |
| `format_state_code(status)`                 | Converts status to a compact display string               | `state = format_state_code('reachable')`                     |
| `format_gb_short(size_gb)`                 | Formats a size in GB                                     | `format_gb_short(12.5)`                                      |
| `format_free_value(free_gb, free_pct)`      | Colors output for free-space percentage                   | `format_free_value(20.5, 85)`                                |
| `get_health_status(percent_used)`           | Returns OK/WARN/CRIT strings                             | `get_health_status(92)`                                       |
| `build_extended_table(groups, ...)`         | Builds a Rich table for a full disk report                | `table = build_extended_table(groups, host, checked_at)`      |
+---------------------------------------------+-----------------------------------------------------------+---------------------------------------------------------------+

---

## Example: build a small page

```python
from OV import OV

ov = OV()

ov.Head()
ov.Body()
ov.Div(id_name="wrapper", style="padding: 20px;")
ov.H("System Status", class_name="2")
ov.P("All services are running normally.", class_name="status")
ov.AStart("/details", class_name="btn")
ov.Bold("View details")
ov.AEnd()
ov.DivEnd()
ov.BodyEnd()
ov.HeadEnd()
```

This generates a compact HTML structure suitable for a dashboard or admin page.

---

## Example: build a table

```python
from OV import OV

ov = OV()
ov.TblStart(border="1", width="100%", class_name="report")
ov.TblStartLine(align="left")
ov.TblEntete("Name")
ov.TblEntete("Value")
ov.TblEndLine()

ov.TblStartLine()
ov.TblCell("CPU")
ov.TblCell("12%")
ov.TblEndLine()

ov.TblStartLine()
ov.TblCell("Memory")
ov.TblCell("68%")
ov.TblEndLine()

ov.TblEnd()
```

This is useful for simple admin tables, status panels, and monitoring screens.

---

## Example: generate tooltips and list items

```python
from OV import ovl, li, make_bar

html = ovl("/docs", "'Open documentation'", "Docs")
print(html)

print(li("First item"))
print(make_bar("/help[, ]Help text[, ]Help"))
```

The `ovl()` helper is useful when you want a link that pops a tooltip using OverLib conventions.

---

## Example: print HTML escaped output

```python
from OV import pr_html

content = {"server": "web01", "status": "online"}
print(pr_html(content, as_return=True))
```

Output is wrapped in a `<pre>` block and HTML-escaped for display.

---

## Example: disk monitoring

```python
from OV import get_disk_usage_data, classify_entry, format_free_value

rows = get_disk_usage_data()
if rows:
    for row in rows:
        group = classify_entry(row)
        usage = row["used_kb"] / row["total_kb"] * 100 if row["total_kb"] else 0
        free_gb = row["free_kb"] / (1024 * 1024)
        print(group, row["mountpoint"], format_free_value(free_gb, 100 - usage))
```

This is a good example for a system monitor or admin dashboard widget.

---

## Best practices

- Use `OV` methods when you want quick HTML output without rendering templates.
- Use string-returning helpers like `ovl()` or `pr_html(as_return=True)` when you need to embed generated markup into a larger page.
- Keep your app logic separate from the HTML generation when possible.
- For richer UI styling, combine `OV` output with CSS classes and a modern CSS layout.

---

## Notes

This module is intentionally simple and practical. It is useful for:

- small dashboard pages
- quick admin tools
- HTML snippets embedded into Flask/Django-style apps
- older web utilities that still use classic HTML structure

If your app grows, you may later prefer a proper template engine such as Jinja2 or Django templates, but `OV.py` remains a convenient quick-start helper module.

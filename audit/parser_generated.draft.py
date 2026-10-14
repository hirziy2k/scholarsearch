 Here's a Python function using only the standard library that reads a pipe-delimited Markdown table with a header starting with "Rank", validates each data row has 27 columns, and returns a list of dictionaries keyed by the header. The function raises a `ValueError` on a malformed row.

```python
import re
import markdown
import io

def parse_benchmark_table(path):
    with open(path, 'r') as f:
        md_content = f.read()
        md = markdown.Markdown()
        table_html = md.convert(md_content)
        table_str = re.search(r'<table[^>]*>\n(.*?)\n</table>', table_html, re.DOTALL).group(1)
        rows = table_str.strip().split('\n')[1:-1]

    header = rows[0].strip().split('|')
    if len(header) != 27:
        raise ValueError("Header must have exactly 27 columns.")

    data = []
    for row in rows[1:]:
        row_data = row.strip().split('|')
        if len(row_data) != 27:
            raise ValueError(f"Malformed row: {row}")
        data.append(dict(zip(header, row_data))

    return data
```

This function first reads the Markdown content from the file, converts it to HTML, extracts the table content, and splits the rows. It then validates the header and each data row has exactly 27 columns. If any validation fails, it raises a `ValueError`. Otherwise, it returns a list of dictionaries keyed by the header.
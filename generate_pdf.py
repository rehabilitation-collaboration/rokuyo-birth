"""Convert manuscript.md to PDF via weasyprint."""
from pathlib import Path
import markdown
from weasyprint import HTML

BASE_DIR = Path(__file__).parent
INPUT = "manuscript.md"
OUTPUT = "output/manuscript.pdf"

CSS = """
@page {
    size: letter;
    margin: 2.5cm;
    @bottom-center { content: counter(page); font-size: 10pt; }
}
body {
    font-family: "Times New Roman", Times, serif;
    font-size: 12pt;
    line-height: 1.8;
    color: #000;
}
h1 { font-size: 16pt; text-align: center; margin-bottom: 0.5em; }
h2 { font-size: 14pt; margin-top: 1.5em; }
h3 { font-size: 12pt; margin-top: 1.2em; }
p { text-align: justify; margin-bottom: 0.8em; }
table {
    border-collapse: collapse;
    width: 100%;
    margin: 1em 0;
    font-size: 10pt;
}
th, td {
    border: 1px solid #000;
    padding: 4px 8px;
    text-align: left;
}
th { background-color: #f0f0f0; font-weight: bold; }
hr { border: none; border-top: 1px solid #ccc; margin: 1.5em 0; }
sup { font-size: 0.8em; }
img { max-width: 100%; height: auto; margin: 1em 0; }
"""

with open(INPUT, encoding="utf-8") as f:
    md_text = f.read()

html_body = markdown.markdown(md_text, extensions=["tables", "smarty"])

html_doc = f"""<!DOCTYPE html>
<html lang="en">
<head><meta charset="utf-8"><style>{CSS}</style></head>
<body>{html_body}</body>
</html>"""

HTML(string=html_doc, base_url=str(BASE_DIR)).write_pdf(OUTPUT)
print(f"PDF generated: {OUTPUT}")

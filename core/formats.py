"""Import / export: DOCX (right-to-left), TXT, HTML, Markdown, JSON, CSV, TEI-XML, EPUB, and .seforim packages.
PDF export is done by the app window's built-in Print → Save as PDF (keeps all Hebrew fonts)."""
import csv
import html
import io
import json
import os
import re
import uuid
import zipfile
from html.parser import HTMLParser

from . import hebrew as H

HE_FONT_DEFAULT = "David"


# ======================================================================== HTML → DOCX
class _DocxBuilder(HTMLParser):
    BLOCK = {"p", "div", "h1", "h2", "h3", "h4", "li", "blockquote", "pre", "tr"}

    def __init__(self, doc, font, size):
        super().__init__(convert_charrefs=True)
        self.doc, self.font, self.size = doc, font, size
        self.par = None
        self.style = [{}]
        self.list_kind = []

    def _cur(self):
        return self.style[-1]

    def _ensure_par(self, tag="p", attrs=None):
        if self.par is None:
            self.par = self._new_par(tag, attrs or {})
        return self.par

    def _new_par(self, tag, attrs):
        from docx.enum.text import WD_ALIGN_PARAGRAPH
        style = None
        if tag in ("h1", "h2", "h3", "h4"):
            style = "Heading " + tag[1]
        elif tag == "li":
            style = "List Number" if self.list_kind and self.list_kind[-1] == "ol" else "List Bullet"
        try:
            p = self.doc.add_paragraph(style=style) if style else self.doc.add_paragraph()
        except KeyError:
            p = self.doc.add_paragraph()
        css = _css(attrs.get("style", ""))
        align = css.get("text-align") or attrs.get("align")
        rtl = (attrs.get("dir") or css.get("direction") or "rtl") != "ltr"
        _set_par_rtl(p, rtl)
        # In bidi paragraphs Word treats left/right as start/end, so leave natural (right) alignment alone.
        if align in ("center", "justify"):
            p.alignment = WD_ALIGN_PARAGRAPH.CENTER if align == "center" else WD_ALIGN_PARAGRAPH.JUSTIFY
        elif rtl and align == "left":
            p.alignment = WD_ALIGN_PARAGRAPH.RIGHT  # = physical left inside an RTL paragraph
        elif not rtl and align == "right":
            p.alignment = WD_ALIGN_PARAGRAPH.RIGHT
        if tag == "blockquote":
            from docx.shared import Pt
            p.paragraph_format.right_indent = Pt(24); p.paragraph_format.left_indent = Pt(24)
        return p

    def handle_starttag(self, tag, attrs):
        a = dict(attrs)
        st = dict(self._cur())
        css = _css(a.get("style", ""))
        if tag in ("b", "strong") or css.get("font-weight") in ("bold", "700", "800", "900"): st["b"] = True
        if tag in ("i", "em") or css.get("font-style") == "italic": st["i"] = True
        if tag == "u" or "underline" in css.get("text-decoration", ""): st["u"] = True
        if tag in ("s", "strike", "del"): st["s"] = True
        if tag == "sup": st["sup"] = True
        if tag == "sub": st["sub"] = True
        if tag in ("h1", "h2", "h3", "h4"): st["b"] = True
        if tag == "font" and a.get("face"): st["font"] = a["face"]
        if tag == "font" and a.get("color"): st["color"] = a["color"]
        if css.get("font-family"): st["font"] = css["font-family"].split(",")[0].strip("'\" ")
        if css.get("font-size"):
            m = re.match(r"([\d.]+)(pt|px|em)?", css["font-size"])
            if m:
                v = float(m.group(1)); unit = m.group(2) or "px"
                st["size"] = v if unit == "pt" else v * 0.75 if unit == "px" else v * self.size
        if css.get("color"): st["color"] = css["color"]
        if css.get("background-color") or tag == "mark": st["hl"] = True
        self.style.append(st)
        if tag in ("ul", "ol"):
            self.list_kind.append(tag)
        if tag in self.BLOCK:
            self.par = self._new_par(tag, a)
        if tag == "br":
            self._ensure_par().add_run().add_break()
        if tag == "hr":
            self.par = None
            self.doc.add_paragraph("―" * 20).alignment = 1

    def handle_startendtag(self, tag, attrs):
        if tag == "br":
            self._ensure_par().add_run().add_break()
        elif tag == "hr":
            self.par = None
            self.doc.add_paragraph("―" * 20).alignment = 1

    def handle_endtag(self, tag):
        if len(self.style) > 1:
            self.style.pop()
        if tag in ("ul", "ol") and self.list_kind:
            self.list_kind.pop()
        if tag in self.BLOCK:
            self.par = None

    def handle_data(self, data):
        if not data.strip() and self.par is None:
            return
        p = self._ensure_par()
        st = self._cur()
        run = p.add_run(data)
        _style_run(run, st.get("font") or self.font, st.get("size") or self.size)
        run.bold, run.italic, run.underline = st.get("b"), st.get("i"), st.get("u")
        if st.get("s"): run.font.strike = True
        if st.get("sup"): run.font.superscript = True
        if st.get("sub"): run.font.subscript = True
        if st.get("color"):
            from docx.shared import RGBColor
            c = _color(st["color"])
            if c: run.font.color.rgb = RGBColor(*c)
        if st.get("hl"):
            from docx.enum.text import WD_COLOR_INDEX
            run.font.highlight_color = WD_COLOR_INDEX.YELLOW


def _css(s):
    out = {}
    for part in (s or "").split(";"):
        if ":" in part:
            k, v = part.split(":", 1)
            out[k.strip().lower()] = v.strip().lower() if k.strip().lower() != "font-family" else v.strip()
    return out


def _color(c):
    c = c.strip()
    m = re.match(r"#([0-9a-f]{6})", c, re.I)
    if m:
        h = m.group(1); return tuple(int(h[i:i + 2], 16) for i in (0, 2, 4))
    m = re.match(r"#([0-9a-f]{3})$", c, re.I)
    if m:
        return tuple(int(x * 2, 16) for x in m.group(1))
    m = re.match(r"rgb\((\d+),\s*(\d+),\s*(\d+)", c)
    if m:
        return tuple(int(x) for x in m.groups())
    return None


def _set_par_rtl(p, rtl=True):
    from docx.oxml.ns import qn
    from docx.oxml import OxmlElement
    pPr = p._p.get_or_add_pPr()
    for el in pPr.findall(qn("w:bidi")):
        pPr.remove(el)
    if rtl:
        b = OxmlElement("w:bidi"); b.set(qn("w:val"), "1"); pPr.append(b)


def _style_run(run, font, size):
    from docx.oxml.ns import qn
    from docx.oxml import OxmlElement
    from docx.shared import Pt
    run.font.name = font
    run.font.size = Pt(size)
    rPr = run._r.get_or_add_rPr()
    rFonts = rPr.find(qn("w:rFonts"))
    if rFonts is None:
        rFonts = OxmlElement("w:rFonts"); rPr.append(rFonts)
    for attr in ("w:ascii", "w:hAnsi", "w:cs", "w:eastAsia"):
        rFonts.set(qn(attr), font)
    szcs = OxmlElement("w:szCs"); szcs.set(qn("w:val"), str(int(size * 2)))
    sz = rPr.find(qn("w:sz"))
    if sz is not None:
        sz.addnext(szcs)
    else:
        rPr.append(szcs)
    if H.has_hebrew(run.text):
        rtl = OxmlElement("w:rtl"); rtl.set(qn("w:val"), "1"); rPr.append(rtl)
        lang = OxmlElement("w:lang"); lang.set(qn("w:bidi"), "he-IL"); rPr.append(lang)


def _sect_bidi(doc):
    from docx.oxml import OxmlElement
    from docx.oxml.ns import qn
    sectPr = doc.sections[0]._sectPr
    b = OxmlElement("w:bidi")
    grid = sectPr.find(qn("w:docGrid"))
    if grid is not None:
        grid.addprevious(b)
    else:
        sectPr.append(b)


def html_to_docx(html_text, path, title="", font=HE_FONT_DEFAULT, size=14, page_breaks_on_hr=False):
    from docx import Document
    from docx.shared import Pt
    from docx.oxml.ns import qn
    doc = Document()
    _sect_bidi(doc)
    st = doc.styles["Normal"]
    st.font.name = font; st.font.size = Pt(size)
    st.element.rPr.rFonts.set(qn("w:cs"), font)
    if title:
        p = doc.add_paragraph(style="Title"); _set_par_rtl(p, H.has_hebrew(title))
        r = p.add_run(title); _style_run(r, font, size + 10)
        p.alignment = 1
    _DocxBuilder(doc, font, size).feed(html_text or "")
    doc.core_properties.title = title or "Seforim Studio document"
    doc.save(path)
    return path


def text_to_docx(text, path, title="", font=HE_FONT_DEFAULT, size=14, pages=None):
    """Plain text (keeps line breaks). pages = list of page texts -> one page each."""
    from docx import Document
    from docx.enum.text import WD_BREAK
    from docx.shared import Pt
    from docx.oxml import OxmlElement
    doc = Document()
    _sect_bidi(doc)
    doc.styles["Normal"].font.name = font
    doc.styles["Normal"].font.size = Pt(size)
    if title:
        p = doc.add_paragraph(style="Title"); _set_par_rtl(p); _style_run(p.add_run(title), font, size + 10)
    pages = pages if pages is not None else [text]
    for i, page in enumerate(pages):
        for line in page.split("\n"):
            p = doc.add_paragraph()
            _set_par_rtl(p, H.has_hebrew(line) or not line.strip())
            if line:
                _style_run(p.add_run(line), font, size)
        if i < len(pages) - 1:
            doc.add_paragraph().add_run().add_break(WD_BREAK.PAGE)
    doc.save(path)
    return path


# ======================================================================== other export formats
def html_to_text(h):
    h = re.sub(r"<(br|/p|/div|/h\d|/li|/tr)[^>]*>", "\n", h or "", flags=re.I)
    h = re.sub(r"<li[^>]*>", "• ", h, flags=re.I)
    return html.unescape(re.sub(r"<[^>]+>", "", h)).strip()


def html_to_markdown(h):
    s = h or ""
    for n in range(4, 0, -1):
        s = re.sub(rf"<h{n}[^>]*>(.*?)</h{n}>", lambda m, n=n: "\n" + "#" * n + " " + m.group(1) + "\n", s, flags=re.S | re.I)
    s = re.sub(r"<(b|strong)[^>]*>(.*?)</\1>", r"**\2**", s, flags=re.S | re.I)
    s = re.sub(r"<(i|em)[^>]*>(.*?)</\1>", r"*\2*", s, flags=re.S | re.I)
    s = re.sub(r"<blockquote[^>]*>(.*?)</blockquote>", lambda m: "\n> " + m.group(1) + "\n", s, flags=re.S | re.I)
    return html_to_text(s)


def full_html(body, title="", font="'Frank Ruhl Libre', 'David', serif"):
    return f"""<!doctype html><html lang="he" dir="rtl"><head><meta charset="utf-8"><title>{html.escape(title)}</title>
<style>body{{font-family:{font};font-size:18px;line-height:1.7;max-width:800px;margin:40px auto;padding:0 20px;}}
.en{{direction:ltr;text-align:left;font-family:Georgia,serif;color:#333}} .ref{{color:#8a6d3b;font-size:.8em}}</style></head>
<body>{f'<h1>{html.escape(title)}</h1>' if title else ''}{body}</body></html>"""


def passages_to_html(passages, title="", show_en=True):
    out = []
    for p in passages:
        out.append(f"<p><span class='ref'>{html.escape(p.get('ref', ''))}</span><br>{html.escape(p.get('he') or '')}</p>")
        if show_en and p.get("en"):
            out.append(f"<p class='en'>{html.escape(p['en'])}</p>")
    return full_html("\n".join(out), title)


def to_tei(passages, title, author=""):
    body = []
    for p in passages:
        body.append(f'  <div type="segment" n="{html.escape(p.get("ref", ""))}">\n'
                    f'    <p xml:lang="he">{html.escape(p.get("he") or "")}</p>\n'
                    + (f'    <p xml:lang="en">{html.escape(p["en"])}</p>\n' if p.get("en") else "") + "  </div>")
    return f"""<?xml version="1.0" encoding="UTF-8"?>
<TEI xmlns="http://www.tei-c.org/ns/1.0">
 <teiHeader><fileDesc><titleStmt><title>{html.escape(title)}</title><author>{html.escape(author)}</author></titleStmt>
  <publicationStmt><p>Exported by Seforim Studio (offline)</p></publicationStmt>
  <sourceDesc><p>Sefaria export / user library</p></sourceDesc></fileDesc></teiHeader>
 <text xml:lang="he"><body>
{chr(10).join(body)}
 </body></text>
</TEI>"""


def to_csv(rows, headers=None):
    buf = io.StringIO()
    w = csv.writer(buf)
    if rows and isinstance(rows[0], dict):
        headers = headers or list(rows[0].keys())
        w.writerow(headers)
        for r in rows:
            w.writerow([r.get(h, "") for h in headers])
    else:
        if headers: w.writerow(headers)
        w.writerows(rows)
    return "﻿" + buf.getvalue()  # BOM so Excel opens Hebrew correctly


def to_epub(chapters, path, title, author="", lang="he"):
    """chapters: list of (chapter title, html body)."""
    uid = str(uuid.uuid4())
    with zipfile.ZipFile(path, "w") as z:
        z.writestr("mimetype", "application/epub+zip", compress_type=zipfile.ZIP_STORED)
        z.writestr("META-INF/container.xml", '<?xml version="1.0"?><container version="1.0" xmlns="urn:oasis:names:tc:opendocument:xmlns:container">'
                   '<rootfiles><rootfile full-path="OEBPS/content.opf" media-type="application/oebps-package+xml"/></rootfiles></container>')
        items, spine, nav = [], [], []
        for i, (ct, body) in enumerate(chapters):
            fn = f"ch{i + 1}.xhtml"
            z.writestr("OEBPS/" + fn, f'<?xml version="1.0" encoding="utf-8"?><html xmlns="http://www.w3.org/1999/xhtml" xml:lang="{lang}" dir="rtl">'
                       f'<head><title>{html.escape(ct)}</title><style>body{{direction:rtl;font-family:serif;line-height:1.6}}</style></head>'
                       f'<body><h2>{html.escape(ct)}</h2>{_xhtml(body)}</body></html>')
            items.append(f'<item id="c{i}" href="{fn}" media-type="application/xhtml+xml"/>')
            spine.append(f'<itemref idref="c{i}"/>')
            nav.append(f'<li><a href="{fn}">{html.escape(ct)}</a></li>')
        z.writestr("OEBPS/nav.xhtml", f'<?xml version="1.0" encoding="utf-8"?><html xmlns="http://www.w3.org/1999/xhtml" xmlns:epub="http://www.idpf.org/2007/ops" dir="rtl">'
                   f'<head><title>{html.escape(title)}</title></head><body><nav epub:type="toc"><ol>{"".join(nav)}</ol></nav></body></html>')
        z.writestr("OEBPS/content.opf", f'<?xml version="1.0" encoding="utf-8"?><package xmlns="http://www.idpf.org/2007/opf" version="3.0" unique-identifier="uid">'
                   f'<metadata xmlns:dc="http://purl.org/dc/elements/1.1/"><dc:identifier id="uid">{uid}</dc:identifier><dc:title>{html.escape(title)}</dc:title>'
                   f'<dc:creator>{html.escape(author)}</dc:creator><dc:language>{lang}</dc:language><meta property="dcterms:modified">2026-01-01T00:00:00Z</meta></metadata>'
                   f'<manifest><item id="nav" href="nav.xhtml" media-type="application/xhtml+xml" properties="nav"/>{"".join(items)}</manifest>'
                   f'<spine page-progression-direction="rtl">{"".join(spine)}</spine></package>')
    return path


def _xhtml(body):
    body = re.sub(r"<br\s*>", "<br/>", body or "")
    body = re.sub(r"<hr\s*>", "<hr/>", body)
    body = re.sub(r"<img([^>]*?)(?<!/)>", r"<img\1/>", body)
    return body.replace("&nbsp;", "&#160;")


# ======================================================================== importers
def import_file(path):
    """Return (title, html, plain_text) for txt, md, html, docx, pdf, epub, json(.seforim doc)."""
    ext = os.path.splitext(path)[1].lower()
    title = os.path.splitext(os.path.basename(path))[0]
    if ext in (".txt", ".md", ".csv", ".tsv"):
        with open(path, encoding="utf-8-sig", errors="replace") as f:
            t = f.read()
        h = "".join(f"<p>{html.escape(l)}</p>" if l.strip() else "<p><br></p>" for l in t.splitlines())
        if ext == ".md":
            h = re.sub(r"<p>(#+)\s*(.*?)</p>", lambda m: f"<h{len(m.group(1))}>{m.group(2)}</h{len(m.group(1))}>", h)
        return title, h, t
    if ext in (".html", ".htm"):
        with open(path, encoding="utf-8", errors="replace") as f:
            h = f.read()
        m = re.search(r"<body[^>]*>(.*)</body>", h, re.S | re.I)
        body = m.group(1) if m else h
        body = re.sub(r"<script.*?</script>|<style.*?</style>", "", body, flags=re.S | re.I)
        return title, body, html_to_text(body)
    if ext == ".docx":
        return (title,) + docx_to_html(path)
    if ext == ".pdf":
        pages = pdf_text_pages(path)
        t = "\n\n".join(pages)
        return title, "".join(f"<p>{html.escape(l)}</p>" for l in t.splitlines() if l.strip()), t
    if ext == ".epub":
        parts = []
        with zipfile.ZipFile(path) as z:
            for n in sorted(z.namelist()):
                if n.endswith((".xhtml", ".html", ".htm")):
                    parts.append(re.sub(r"<script.*?</script>", "", z.read(n).decode("utf-8", "replace"), flags=re.S))
        body = "".join(re.search(r"<body[^>]*>(.*)</body>", p, re.S).group(1) if re.search(r"<body", p) else p for p in parts)
        return title, body, html_to_text(body)
    if ext in (".json",):
        with open(path, encoding="utf-8") as f:
            js = json.load(f)
        if isinstance(js, dict) and "html" in js:
            return js.get("title", title), js["html"], html_to_text(js["html"])
        return title, f"<pre>{html.escape(json.dumps(js, ensure_ascii=False, indent=1)[:200000])}</pre>", ""
    raise ValueError(f"Unsupported file type: {ext}")


def docx_to_html(path):
    from docx import Document
    doc = Document(path)
    out, plain = [], []
    for p in doc.paragraphs:
        runs = []
        for r in p.runs:
            t = html.escape(r.text)
            if not t:
                continue
            if r.bold: t = f"<b>{t}</b>"
            if r.italic: t = f"<i>{t}</i>"
            if r.underline: t = f"<u>{t}</u>"
            runs.append(t)
        sty = (p.style.name or "").lower() if p.style is not None else ""
        tag = "h1" if sty.startswith("heading 1") or sty == "title" else "h2" if sty.startswith("heading 2") else "h3" if sty.startswith("heading") else "p"
        out.append(f"<{tag}>{''.join(runs) or '<br>'}</{tag}>")
        plain.append(p.text)
    for t in doc.tables:
        rows = "".join("<tr>" + "".join(f"<td>{html.escape(c.text)}</td>" for c in r.cells) + "</tr>" for r in t.rows)
        out.append(f"<table border='1'>{rows}</table>")
        plain += ["\t".join(c.text for c in r.cells) for r in t.rows]
    return "".join(out), "\n".join(plain)


_UNIT = re.compile(r"[א-ת֑-ׇ׳״]+|[A-Za-zÀ-ɏ]+|\d+|\s+|.", re.S)


def _is_ltr_unit(u):
    return bool(re.match(r"[A-Za-zÀ-ɏ\d]", u))


def visual_to_logical(line):
    """Convert a right-to-left line that a PDF gave in visual (left-to-right) order into logical order.
    Hebrew letter runs are already logical; we reverse the run order but keep English/number groups intact."""
    units = _UNIT.findall(line)
    groups, i = [], 0
    while i < len(units):
        if _is_ltr_unit(units[i]):
            j = i
            k = i + 1
            while k < len(units) and not H.has_hebrew(units[k]):
                if _is_ltr_unit(units[k]):
                    j = k
                k += 1
            groups.append("".join(units[i:j + 1]))
            i = j + 1
        else:
            groups.append(units[i]); i += 1
    out = "".join(reversed(groups)).strip()
    out = re.sub(r"\)([^()]*)\)", r"(\1)", out)
    out = re.sub(r"\(([^()]*)\(", r"(\1)", out)
    out = re.sub(r"\]([^\[\]]*)\]", r"[\1]", out)
    return out


def looks_visual(lines):
    """Heuristic: in visual-order RTL text, sentence punctuation shows up at the START of lines."""
    heb = [l.strip() for l in lines if H.has_hebrew(l) and l.strip()]
    if not heb:
        return False
    starts = sum(1 for l in heb if l[0] in ".,:;!?׃" and H.has_hebrew(l[1:3]))
    ends = sum(1 for l in heb if l[-1] in ".,:;!?׃")
    return starts > ends


def pdf_text_pages(path, order="auto"):
    """Text layer of a PDF (no OCR). Returns list of page strings ('' for scanned pages).
    order: 'auto' | 'visual' (fix reversed Hebrew) | 'logical' (leave as is)."""
    import pypdfium2 as pdfium
    out = []
    pdf = pdfium.PdfDocument(path)
    try:
        for i in range(len(pdf)):
            tp = pdf[i].get_textpage()
            t = (tp.get_text_range() or "").replace("\r\n", "\n")
            lines = [l.rstrip() for l in t.splitlines()]
            fix = order == "visual" or (order == "auto" and looks_visual(lines))
            if fix:
                lines = [visual_to_logical(l) if H.has_hebrew(l) and len(H.RE_HEB.findall(l)) >= len(H.RE_LAT.findall(l)) else l for l in lines]
            out.append("\n".join(lines).strip())
    finally:
        pdf.close()
    return out


# ======================================================================== .seforim share package
def make_package(path, kind, items, meta=None):
    """A zip with manifest.json + items.json (+ optional files). Used for LAN/Bluetooth sharing and backup."""
    with zipfile.ZipFile(path, "w", zipfile.ZIP_DEFLATED) as z:
        z.writestr("manifest.json", json.dumps({"app": "Seforim Studio", "version": 1, "kind": kind, "meta": meta or {}}, ensure_ascii=False))
        z.writestr("items.json", json.dumps(items, ensure_ascii=False))
    return path


def read_package(path_or_bytes):
    src = io.BytesIO(path_or_bytes) if isinstance(path_or_bytes, (bytes, bytearray)) else path_or_bytes
    with zipfile.ZipFile(src) as z:
        man = json.loads(z.read("manifest.json"))
        items = json.loads(z.read("items.json"))
    if man.get("app") != "Seforim Studio":
        raise ValueError("Not a Seforim Studio package")
    return man, items

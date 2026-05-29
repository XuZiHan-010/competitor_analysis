from io import BytesIO
from zipfile import ZIP_DEFLATED, ZipFile

from schemas.report import Report


def export_markdown(report: Report) -> bytes:
    return report.markdown_content.encode("utf-8")


def export_pdf(report: Report) -> bytes:
    text = _pdf_text(report.markdown_content)
    stream = f"BT /F1 12 Tf 72 760 Td 14 TL {text} ET".encode("latin-1", errors="replace")
    objects = [
        b"<< /Type /Catalog /Pages 2 0 R >>",
        b"<< /Type /Pages /Kids [3 0 R] /Count 1 >>",
        b"<< /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792] "
        b"/Resources << /Font << /F1 4 0 R >> >> /Contents 5 0 R >>",
        b"<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>",
        b"<< /Length "
        + str(len(stream)).encode("ascii")
        + b" >>\nstream\n"
        + stream
        + b"\nendstream",
    ]
    body = BytesIO()
    body.write(b"%PDF-1.4\n")
    offsets: list[int] = []
    for index, obj in enumerate(objects, start=1):
        offsets.append(body.tell())
        body.write(f"{index} 0 obj\n".encode("ascii"))
        body.write(obj)
        body.write(b"\nendobj\n")
    xref_offset = body.tell()
    body.write(f"xref\n0 {len(objects) + 1}\n".encode("ascii"))
    body.write(b"0000000000 65535 f \n")
    for offset in offsets:
        body.write(f"{offset:010d} 00000 n \n".encode("ascii"))
    body.write(
        (
            f"trailer << /Size {len(objects) + 1} /Root 1 0 R >>\n"
            f"startxref\n{xref_offset}\n%%EOF\n"
        ).encode("ascii")
    )
    return body.getvalue()


def export_pptx(report: Report) -> bytes:
    title = _xml_escape(str(report.structured_content.get("summary") or "Competitor Analysis"))
    body = _xml_escape(_trim(report.markdown_content, 1200))
    data = BytesIO()
    with ZipFile(data, "w", ZIP_DEFLATED) as archive:
        archive.writestr("[Content_Types].xml", _content_types())
        archive.writestr("_rels/.rels", _root_rels())
        archive.writestr("ppt/presentation.xml", _presentation())
        archive.writestr("ppt/_rels/presentation.xml.rels", _presentation_rels())
        archive.writestr("ppt/slides/slide1.xml", _slide(title, body))
    return data.getvalue()


def _pdf_text(markdown: str) -> str:
    lines = [_escape_pdf_line(line.strip()) for line in markdown.splitlines() if line.strip()]
    return " ".join(f"({line}) Tj T*" for line in lines[:35])


def _escape_pdf_line(line: str) -> str:
    return _trim(line, 110).replace("\\", "\\\\").replace("(", "\\(").replace(")", "\\)")


def _trim(value: str, limit: int) -> str:
    return value if len(value) <= limit else value[: limit - 1] + "..."


def _xml_escape(value: str) -> str:
    return (
        value.replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
        .replace('"', "&quot;")
        .replace("'", "&apos;")
    )


def _content_types() -> str:
    presentation_type = (
        "application/vnd.openxmlformats-officedocument." "presentationml.presentation.main+xml"
    )
    slide_type = "application/vnd.openxmlformats-officedocument.presentationml.slide+xml"
    return f"""<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">
  <Default Extension="rels"
    ContentType="application/vnd.openxmlformats-package.relationships+xml"/>
  <Default Extension="xml" ContentType="application/xml"/>
  <Override PartName="/ppt/presentation.xml" ContentType="{presentation_type}"/>
  <Override PartName="/ppt/slides/slide1.xml" ContentType="{slide_type}"/>
</Types>"""


def _root_rels() -> str:
    return """<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">
  <Relationship Id="rId1"
    Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/officeDocument"
    Target="ppt/presentation.xml"/>
</Relationships>"""


def _presentation() -> str:
    return """<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<p:presentation xmlns:p="http://schemas.openxmlformats.org/presentationml/2006/main"
 xmlns:a="http://schemas.openxmlformats.org/drawingml/2006/main"
 xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships">
  <p:sldIdLst><p:sldId id="256" r:id="rId1"/></p:sldIdLst>
  <p:sldSz cx="12192000" cy="6858000" type="wide"/>
</p:presentation>"""


def _presentation_rels() -> str:
    return """<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">
  <Relationship Id="rId1"
    Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/slide"
    Target="slides/slide1.xml"/>
</Relationships>"""


def _slide(title: str, body: str) -> str:
    return f"""<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<p:sld xmlns:p="http://schemas.openxmlformats.org/presentationml/2006/main"
 xmlns:a="http://schemas.openxmlformats.org/drawingml/2006/main"
 xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships">
  <p:cSld><p:spTree>
    <p:nvGrpSpPr><p:cNvPr id="1" name=""/><p:cNvGrpSpPr/><p:nvPr/></p:nvGrpSpPr>
    <p:grpSpPr>
      <a:xfrm><a:off x="0" y="0"/><a:ext cx="0" cy="0"/>
        <a:chOff x="0" y="0"/><a:chExt cx="0" cy="0"/>
      </a:xfrm>
    </p:grpSpPr>
    <p:sp><p:nvSpPr><p:cNvPr id="2" name="Title"/><p:cNvSpPr/><p:nvPr/></p:nvSpPr>
      <p:spPr>
        <a:xfrm><a:off x="685800" y="457200"/><a:ext cx="10972800" cy="914400"/></a:xfrm>
      </p:spPr>
      <p:txBody><a:bodyPr/><a:lstStyle/>
        <a:p><a:r><a:rPr sz="3400"/><a:t>{title}</a:t></a:r></a:p>
      </p:txBody>
    </p:sp>
    <p:sp><p:nvSpPr><p:cNvPr id="3" name="Body"/><p:cNvSpPr/><p:nvPr/></p:nvSpPr>
      <p:spPr>
        <a:xfrm><a:off x="685800" y="1600200"/><a:ext cx="10972800" cy="4572000"/></a:xfrm>
      </p:spPr>
      <p:txBody><a:bodyPr wrap="square"/><a:lstStyle/>
        <a:p><a:r><a:rPr sz="1800"/><a:t>{body}</a:t></a:r></a:p>
      </p:txBody>
    </p:sp>
  </p:spTree></p:cSld><p:clrMapOvr><a:masterClrMapping/></p:clrMapOvr>
</p:sld>"""

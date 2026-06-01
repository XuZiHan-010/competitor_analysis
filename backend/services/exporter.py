from io import BytesIO

from schemas.report import Report


def export_markdown(report: Report) -> bytes:
    return report.markdown_content.encode("utf-8")


def export_pdf(report: Report) -> bytes:
    stream = _pdf_text_stream(report.markdown_content)
    objects = [
        b"<< /Type /Catalog /Pages 2 0 R >>",
        b"<< /Type /Pages /Kids [3 0 R] /Count 1 >>",
        b"<< /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792] "
        b"/Resources << /Font << /F1 4 0 R >> >> /Contents 5 0 R >>",
        b"<< /Type /Font /Subtype /Type0 /BaseFont /STSong-Light "
        b"/Encoding /UniGB-UCS2-H /DescendantFonts [6 0 R] >>",
        b"<< /Length "
        + str(len(stream)).encode("ascii")
        + b" >>\nstream\n"
        + stream
        + b"\nendstream",
        b"<< /Type /Font /Subtype /CIDFontType0 /BaseFont /STSong-Light "
        b"/CIDSystemInfo << /Registry (Adobe) /Ordering (GB1) /Supplement 5 >> "
        b"/FontDescriptor 7 0 R >>",
        b"<< /Type /FontDescriptor /FontName /STSong-Light /Flags 4 "
        b"/FontBBox [0 -120 1000 880] /ItalicAngle 0 /Ascent 880 "
        b"/Descent -120 /CapHeight 880 /StemV 80 >>",
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



def _pdf_text_stream(markdown: str) -> bytes:
    lines = [_trim(line.strip(), 110) for line in markdown.splitlines() if line.strip()]
    commands = ["BT /F1 12 Tf 72 760 Td 14 TL"]
    commands.extend(f"<{_utf16be_hex(line)}> Tj T*" for line in lines[:35])
    commands.append("ET")
    return "\n".join(commands).encode("ascii")


def _utf16be_hex(value: str) -> str:
    return (b"\xfe\xff" + value.encode("utf-16-be")).hex().upper()


def _trim(value: str, limit: int) -> str:
    return value if len(value) <= limit else value[: limit - 1] + "..."



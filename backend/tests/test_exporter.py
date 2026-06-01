from uuid import uuid4

from schemas.report import Report, ReportMetrics
from services.exporter import export_pdf


def test_pdf_export_preserves_chinese_text_as_utf16be() -> None:
    report = Report(
        task_id=uuid4(),
        structured_content={"summary": "中文摘要"},
        markdown_content="# 竞品分析报告\n中文内容：功能矩阵、定价、用户画像",
        sources=[],
        claims=[],
        metrics=ReportMetrics(
            field_coverage_rate=1.0,
            citation_coverage_rate=1.0,
            manual_correction_rate=0.0,
        ),
    )

    pdf = export_pdf(report)
    title_hex = (b"\xfe\xff" + "# 竞品分析报告".encode("utf-16-be")).hex().upper()

    assert pdf.startswith(b"%PDF-1.4")
    assert b"/Subtype /Type0" in pdf
    assert b"/Encoding /UniGB-UCS2-H" in pdf
    assert title_hex.encode("ascii") in pdf
    assert b"46454646" not in pdf

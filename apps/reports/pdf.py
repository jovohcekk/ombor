"""
PDF export architecture.

Production deployments can plug in WeasyPrint or ReportLab without changing views:

    from apps.reports.pdf import render_report_pdf
    pdf_bytes = render_report_pdf(title, headers, rows)

Until a PDF engine is installed, this module raises NotImplementedError so CSV
remains the supported export path.
"""


class PdfExportNotConfigured(NotImplementedError):
    pass


def render_report_pdf(title, headers, rows):
    raise PdfExportNotConfigured(
        "PDF export is architected but not enabled. Install WeasyPrint or ReportLab "
        "and implement render_report_pdf, or keep using CSV export."
    )

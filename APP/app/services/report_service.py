"""Report generation service using Jinja2 + WeasyPrint."""
from __future__ import annotations

import logging
from pathlib import Path
from datetime import datetime
from typing import Any, Dict, List

from jinja2 import Environment, FileSystemLoader, select_autoescape
from weasyprint import HTML, CSS

from app.core.config import settings

logger = logging.getLogger(__name__)


class ReportService:
    """Generate professional audit-ready reports."""

    def __init__(self) -> None:
        self.template_dir = Path(settings.REPORT_TEMPLATE_DIR)
        self.template_dir.mkdir(parents=True, exist_ok=True)
        self.output_dir = Path(settings.REPORT_OUTPUT_DIR)
        self.output_dir.mkdir(parents=True, exist_ok=True)

        self.env = Environment(
            loader=FileSystemLoader(str(self.template_dir)),
            autoescape=select_autoescape(["html", "xml"]),
            trim_blocks=True,
            lstrip_blocks=True,
        )

        self.template_name = "report.html"

    async def generate_report(
        self,
        document_id: int,
        document,
        interventions,
        total_cost: float,
        analysis,
    ) -> str:
        """Render HTML template and export as PDF."""

        context = self._build_context(document, interventions, total_cost, analysis)
        template = self.env.get_template(self.template_name)
        rendered_html = template.render(**context)

        timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
        base_filename = f"report_document_{document_id}_{timestamp}"
        html_path = self.output_dir / f"{base_filename}.html"
        pdf_path = self.output_dir / f"{base_filename}.pdf"

        html_path.write_text(rendered_html, encoding="utf-8")

        css = CSS(string=self._default_css())
        HTML(string=rendered_html, base_url=str(self.template_dir.parent)).write_pdf(
            str(pdf_path),
            stylesheets=[css],
        )

        logger.info("Report generated at %s", pdf_path)
        return str(pdf_path)

    def _build_context(
        self,
        document,
        interventions,
        total_cost: float,
        analysis,
    ) -> Dict[str, Any]:
        """Build context dict for report template."""

        cost_breakdown = []
        for intervention in interventions:
            materials = []
            subtotal = 0.0
            for item in intervention.cost_items:
                materials.append(
                    {
                        "material_name": item.material_name,
                        "specification": item.specification,
                        "quantity": item.quantity,
                        "unit": item.unit,
                        "unit_rate": item.unit_rate,
                        "total_cost": item.total_cost,
                        "source": item.price_source,
                        "reference": item.price_source_reference,
                        "fetched_at": item.price_fetched_at,
                    }
                )
                subtotal += item.total_cost

            cost_breakdown.append(
                {
                    "intervention_type": intervention.intervention_type,
                    "description": intervention.description,
                    "location": intervention.location,
                    "chainage": intervention.chainage,
                    "irc_standards": intervention.irc_standards or [],
                    "irc_clauses": intervention.irc_clauses or [],
                    "specifications": intervention.specifications or {},
                    "confidence_score": intervention.confidence_score,
                    "materials": materials,
                    "subtotal": subtotal,
                }
            )

        summary = {
            "total_interventions": analysis.total_interventions,
            "total_cost": total_cost,
            "analysis_duration": analysis.analysis_duration_seconds,
            "report_generated_at": analysis.analysis_completed_at or datetime.now(),
        }

        context = {
            "branding": {
                "agency_name": "Ministry of Road Transport & Highways, Government of India",
                "system_name": settings.APP_NAME,
                "logo_path": settings.LOGO_PATH,
            },
            "document": {
                "id": document.id,
                "filename": document.original_filename,
                "uploaded_at": document.created_at,
                "processed_at": document.processing_completed_at,
                "uploaded_by": document.uploaded_by or "Authorized Auditor",
            },
            "summary": summary,
            "interventions": cost_breakdown,
            "assumptions": analysis.assumptions or [],
            "warnings": analysis.warnings or [],
            "pricing_sources": [
                {
                    "name": "CPWD Schedule of Rates",
                    "url": settings.CPWD_SOR_API_URL,
                },
                {
                    "name": "CPWD Analysis of Rates",
                    "url": settings.CPWD_AOR_API_URL,
                },
                {
                    "name": "Government e-Marketplace (GeM)",
                    "url": settings.GEM_API_URL,
                },
            ],
            "generated_on": datetime.now(),
        }

        return context

    def _default_css(self) -> str:
        """Lightweight government-style palette."""

        return """
            @page {
                size: A4;
                margin: 1.2cm;
            }

            body {
                font-family: 'Inter', 'Noto Sans', 'Segoe UI', sans-serif;
                color: #1b263b;
                background: #ffffff;
                font-size: 12px;
            }

            header {
                border-bottom: 2px solid #0a3161;
                padding-bottom: 12px;
                margin-bottom: 18px;
                display: flex;
                align-items: center;
                gap: 16px;
            }

            header img {
                width: 48px;
                height: 48px;
            }

            h1 {
                font-size: 20px;
                color: #0a3161;
                margin: 0;
            }

            h2 {
                font-size: 16px;
                color: #0a3161;
                border-bottom: 1px solid #dfe7f5;
                padding-bottom: 6px;
                margin-top: 24px;
            }

            table {
                width: 100%;
                border-collapse: collapse;
                margin: 12px 0;
                font-size: 11px;
            }

            table th {
                background: #f1f5fb;
                color: #0a3161;
                text-align: left;
                padding: 8px;
                border-bottom: 1px solid #c7d3eb;
            }

            table td {
                padding: 8px;
                border-bottom: 1px solid #e1e7f1;
            }

            .pill {
                display: inline-block;
                padding: 2px 8px;
                background: #e7ecf8;
                color: #0a3161;
                border-radius: 12px;
                font-size: 10px;
                margin-right: 4px;
            }

            .summary-grid {
                display: grid;
                grid-template-columns: repeat(2, 1fr);
                gap: 12px;
                margin-top: 12px;
            }

            .summary-card {
                background: #f9fafc;
                border: 1px solid #e0e6f2;
                border-radius: 8px;
                padding: 10px 12px;
            }

            .summary-card .label {
                font-size: 10px;
                text-transform: uppercase;
                color: #5c6f91;
                letter-spacing: 0.05em;
            }

            .summary-card .value {
                font-size: 16px;
                font-weight: 600;
                margin-top: 4px;
                color: #0f1d3d;
            }

            .alert {
                border-left: 3px solid #c44536;
                background: #fff5f4;
                padding: 8px 12px;
                margin: 8px 0;
                border-radius: 4px;
            }
        """

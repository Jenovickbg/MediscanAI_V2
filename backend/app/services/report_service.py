from __future__ import annotations

import io
from datetime import datetime, timezone
from typing import Any

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import cm
from reportlab.platypus import Image, Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle

from sqlalchemy.orm import Session, joinedload

from app.core.config import settings
from app.models.examen import Examen
from app.models.resultat import ResultatAnalyse, VERTEBRES
from app.services.examen_service import ExamenService
from app.services.pipeline_service import pipeline_service

INSTITUTION_NAME = "Centre Hospitalier Universitaire — Kinshasa"
SUSPICION_THRESHOLD = 0.30


class ReportService:
    def __init__(self) -> None:
        self.examen_service = ExamenService()

    def generate_pdf(self, db: Session, study_id: str) -> bytes:
        examen = self.examen_service.get_examen_by_study_id(db, study_id)
        if examen is None:
            raise ValueError("Examen introuvable")

        resultat = (
            db.query(ResultatAnalyse)
            .options(joinedload(ResultatAnalyse.scores_vertebres))
            .filter(ResultatAnalyse.study_instance_uid == study_id)
            .first()
        )
        if resultat is None:
            raise ValueError("Résultats d'analyse non disponibles")

        buffer = io.BytesIO()
        doc = SimpleDocTemplate(
            buffer,
            pagesize=A4,
            rightMargin=2 * cm,
            leftMargin=2 * cm,
            topMargin=2 * cm,
            bottomMargin=2 * cm,
        )

        styles = getSampleStyleSheet()
        title_style = ParagraphStyle(
            "ReportTitle",
            parent=styles["Heading1"],
            fontSize=16,
            spaceAfter=6,
            textColor=colors.HexColor("#1a2744"),
        )
        heading_style = ParagraphStyle(
            "ReportHeading",
            parent=styles["Heading2"],
            fontSize=12,
            spaceBefore=12,
            spaceAfter=6,
            textColor=colors.HexColor("#1a2744"),
        )
        body_style = ParagraphStyle(
            "ReportBody",
            parent=styles["Normal"],
            fontSize=10,
            leading=14,
            textColor=colors.HexColor("#333333"),
        )
        footer_style = ParagraphStyle(
            "ReportFooter",
            parent=styles["Normal"],
            fontSize=8,
            textColor=colors.HexColor("#666666"),
        )

        story: list[Any] = []

        story.append(Paragraph(f"<b>{INSTITUTION_NAME}</b>", title_style))
        story.append(Paragraph(f"<b>MediScanAI</b> — Rapport d'analyse cervicale", body_style))
        story.append(Spacer(1, 0.4 * cm))

        patient_date = examen.date_examen or examen.uploaded_at
        patient_rows = [
            ["Patient ID", examen.patient_id],
            ["Study UID", examen.study_instance_uid],
            ["Date examen", patient_date.strftime("%d/%m/%Y %H:%M")],
            ["Nombre de coupes", str(examen.nb_coupes)],
        ]
        story.append(Paragraph("Informations patient", heading_style))
        story.extend(self._build_info_table(patient_rows))
        story.append(Spacer(1, 0.3 * cm))

        result_label = (
            "FRACTURE DÉTECTÉE"
            if resultat.fracture_detectee
            else "AUCUNE FRACTURE SIGNIFICATIVE"
        )
        summary_rows = [
            ["Résultat global", result_label],
            ["Score global", f"{resultat.score_global * 100:.1f} %"],
            ["Date analyse", resultat.date_analyse.strftime("%d/%m/%Y %H:%M")],
            ["Durée analyse", f"{resultat.duree_analyse_sec:.1f} s"],
            ["Mode", "Mock" if resultat.mode_mock else "Modèle IA"],
        ]
        story.append(Paragraph("Résumé de l'analyse", heading_style))
        story.extend(self._build_info_table(summary_rows))
        story.append(Spacer(1, 0.3 * cm))

        story.append(Paragraph("Détail par vertèbre (C1–C7)", heading_style))
        story.extend(self._build_vertebra_table(resultat))
        story.append(Spacer(1, 0.3 * cm))

        story.append(Paragraph("Explications du modèle", heading_style))
        for line in resultat.rapport_clinique.splitlines():
            if line.strip():
                story.append(Paragraph(line.replace("&", "&amp;"), body_style))
            else:
                story.append(Spacer(1, 0.15 * cm))

        reference_scores = self._reference_vertebrae(resultat)
        if reference_scores:
            story.append(Spacer(1, 0.3 * cm))
            story.append(Paragraph("Images de référence", heading_style))
            story.extend(
                self._build_reference_images(study_id, examen, reference_scores, body_style)
            )

        generated_at = datetime.now(timezone.utc).strftime("%d/%m/%Y %H:%M UTC")
        story.append(Spacer(1, 0.5 * cm))
        story.append(
            Paragraph(
                f"Rapport généré par MediScanAI v{settings.APP_VERSION} — "
                f"{generated_at} — À valider par un médecin qualifié.",
                footer_style,
            )
        )

        doc.build(story)
        return buffer.getvalue()

    def _build_info_table(self, rows: list[list[str]]) -> list[Any]:
        table = Table(rows, colWidths=[5 * cm, 11 * cm])
        table.setStyle(
            TableStyle(
                [
                    ("FONTNAME", (0, 0), (-1, -1), "Helvetica"),
                    ("FONTSIZE", (0, 0), (-1, -1), 9),
                    ("FONTNAME", (0, 0), (0, -1), "Helvetica-Bold"),
                    ("BACKGROUND", (0, 0), (-1, -1), colors.HexColor("#f5f7fb")),
                    ("BOX", (0, 0), (-1, -1), 0.5, colors.HexColor("#d0d7e6")),
                    ("INNERGRID", (0, 0), (-1, -1), 0.25, colors.HexColor("#d0d7e6")),
                    ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                    ("LEFTPADDING", (0, 0), (-1, -1), 8),
                    ("RIGHTPADDING", (0, 0), (-1, -1), 8),
                    ("TOPPADDING", (0, 0), (-1, -1), 6),
                    ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
                ]
            )
        )
        return [table]

    def _build_vertebra_table(self, resultat: ResultatAnalyse) -> list[Any]:
        scores_by_vertebra = {s.vertebre: s for s in resultat.scores_vertebres}
        rows = [["Vertèbre", "Score", "Statut", "Localisation"]]

        for vertebre in VERTEBRES:
            score = scores_by_vertebra.get(vertebre)
            if score is None:
                rows.append([vertebre, "—", "—", "—"])
                continue
            rows.append(
                [
                    vertebre,
                    f"{score.probabilite * 100:.1f} %",
                    self._status_label(score.probabilite),
                    score.localisation,
                ]
            )

        table = Table(rows, colWidths=[2 * cm, 2.5 * cm, 3.5 * cm, 8 * cm])
        table.setStyle(
            TableStyle(
                [
                    ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                    ("FONTNAME", (0, 1), (-1, -1), "Helvetica"),
                    ("FONTSIZE", (0, 0), (-1, -1), 8),
                    ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#1a2744")),
                    ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
                    ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#f5f7fb")]),
                    ("BOX", (0, 0), (-1, -1), 0.5, colors.HexColor("#d0d7e6")),
                    ("INNERGRID", (0, 0), (-1, -1), 0.25, colors.HexColor("#d0d7e6")),
                    ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                    ("LEFTPADDING", (0, 0), (-1, -1), 6),
                    ("RIGHTPADDING", (0, 0), (-1, -1), 6),
                    ("TOPPADDING", (0, 0), (-1, -1), 5),
                    ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
                ]
            )
        )
        return [table]

    def _build_reference_images(
        self,
        study_id: str,
        examen: Examen,
        reference_scores: list[Any],
        body_style: ParagraphStyle,
    ) -> list[Any]:
        elements: list[Any] = []
        try:
            volume, _ = self.examen_service.dicom_service.load_volume_from_study(examen.dicom_path)
        except Exception:
            elements.append(Paragraph("Images de référence indisponibles.", body_style))
            return elements

        thumb_size = 5.5 * cm
        for score in reference_scores:
            slice_idx = score.coupe_reference
            try:
                slice_png = self.examen_service.dicom_service.render_slice_to_image(
                    volume, slice_idx, "axial"
                )
                gradcam_png = pipeline_service.render_gradcam_png(
                    volume, slice_idx, score.vertebre, overlay=True
                )
            except Exception:
                continue

            elements.append(
                Paragraph(
                    f"<b>{score.vertebre}</b> — Coupe {slice_idx + 1} "
                    f"({score.probabilite * 100:.1f} %)",
                    body_style,
                )
            )
            row = [
                Image(io.BytesIO(slice_png), width=thumb_size, height=thumb_size),
                Image(io.BytesIO(gradcam_png), width=thumb_size, height=thumb_size),
            ]
            img_table = Table([row], colWidths=[thumb_size, thumb_size])
            img_table.setStyle(
                TableStyle(
                    [
                        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                        ("ALIGN", (0, 0), (-1, -1), "CENTER"),
                    ]
                )
            )
            elements.append(img_table)
            elements.append(Spacer(1, 0.2 * cm))

        return elements

    def _reference_vertebrae(self, resultat: ResultatAnalyse) -> list[Any]:
        at_risk = [s for s in resultat.scores_vertebres if s.probabilite >= SUSPICION_THRESHOLD]
        at_risk.sort(key=lambda s: s.probabilite, reverse=True)
        if at_risk:
            return at_risk[:3]
        if resultat.scores_vertebres:
            return [max(resultat.scores_vertebres, key=lambda s: s.probabilite)]
        return []

    def _status_label(self, probability: float) -> str:
        if probability >= 0.60:
            return "Fracture suspectée"
        if probability >= 0.30:
            return "Surveillance"
        return "Normal"


report_service = ReportService()

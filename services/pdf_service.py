"""Clinical PDF Report Generation Service using ReportLab.

Generates structured, professional medical assessment reports for patients,
which are automatically archived to Cloud Storage (Supabase/Firebase).
"""

import io
from datetime import datetime
from reportlab.lib.pagesizes import letter
from reportlab.lib import colors
from reportlab.platypus import (
    SimpleDocTemplate,
    Paragraph,
    Spacer,
    Table,
    TableStyle,
    HRFlowable,
    KeepTogether,
)
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_RIGHT

from models.prediction import Prediction


def generate_assessment_pdf(prediction: Prediction) -> bytes:
    """Generate a clean, clinical PDF report bytes for a given AI Prediction."""
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(
        buffer,
        pagesize=letter,
        rightMargin=40,
        leftMargin=40,
        topMargin=40,
        bottomMargin=40,
    )

    styles = getSampleStyleSheet()

    # Custom styles
    title_style = ParagraphStyle(
        "DocTitle",
        parent=styles["Heading1"],
        fontName="Helvetica-Bold",
        fontSize=20,
        leading=24,
        textColor=colors.HexColor("#0f766e"),
        alignment=TA_LEFT,
    )

    subtitle_style = ParagraphStyle(
        "DocSubtitle",
        parent=styles["Normal"],
        fontName="Helvetica",
        fontSize=10,
        leading=14,
        textColor=colors.HexColor("#64748b"),
        alignment=TA_LEFT,
    )

    section_heading = ParagraphStyle(
        "SectionHeading",
        parent=styles["Heading2"],
        fontName="Helvetica-Bold",
        fontSize=12,
        leading=16,
        textColor=colors.HexColor("#0f172a"),
        spaceBefore=10,
        spaceAfter=6,
    )

    body_style = ParagraphStyle(
        "Body",
        parent=styles["Normal"],
        fontName="Helvetica",
        fontSize=9.5,
        leading=14,
        textColor=colors.HexColor("#334155"),
    )

    body_bold = ParagraphStyle(
        "BodyBold",
        parent=body_style,
        fontName="Helvetica-Bold",
    )

    disclaimer_style = ParagraphStyle(
        "Disclaimer",
        parent=styles["Normal"],
        fontName="Helvetica-Oblique",
        fontSize=8,
        leading=11,
        textColor=colors.HexColor("#64748b"),
        alignment=TA_CENTER,
    )

    elements = []

    # 1. Header & Branding
    patient = prediction.patient
    patient_user = patient.user if patient else None
    patient_name = patient_user.full_name if patient_user else "Patient"
    patient_phone = patient_user.phone if patient_user else "N/A"
    doctor = prediction.reviewing_doctor
    doctor_user = doctor.user if doctor else None
    doctor_name = doctor_user.full_name if doctor_user else "Assigned Clinical Specialist"

    created_date = (
        prediction.created_at.strftime("%d %B %Y at %H:%M UTC")
        if prediction.created_at
        else datetime.utcnow().strftime("%d %B %Y")
    )

    header_table_data = [
        [
            Paragraph("<b>HealthAI Clinical Assessment Report</b>", title_style),
            Paragraph(f"<b>Report ID:</b> #{prediction.id}<br/><b>Date:</b> {created_date}", subtitle_style),
        ]
    ]
    header_table = Table(header_table_data, colWidths=[330, 200])
    header_table.setStyle(
        TableStyle([
            ("VALIGN", (0, 0), (-1, -1), "TOP"),
            ("ALIGN", (1, 0), (1, 0), "RIGHT"),
        ])
    )
    elements.append(header_table)
    elements.append(Spacer(1, 8))
    elements.append(HRFlowable(width="100%", thickness=1.5, color=colors.HexColor("#0f766e"), spaceAfter=14))

    # 2. Patient & Assessment Meta Table
    meta_data = [
        [
            Paragraph("<b>Patient Name:</b>", body_bold),
            Paragraph(patient_name, body_style),
            Paragraph("<b>Age / Gender:</b>", body_bold),
            Paragraph(f"{prediction.age or 'N/A'} yrs / {str(prediction.gender).capitalize() or 'N/A'}", body_style),
        ],
        [
            Paragraph("<b>Contact Phone:</b>", body_bold),
            Paragraph(patient_phone, body_style),
            Paragraph("<b>Reviewing Doctor:</b>", body_bold),
            Paragraph(doctor_name, body_style),
        ],
        [
            Paragraph("<b>BMI / Weight:</b>", body_bold),
            Paragraph(f"{patient.bmi or 'N/A'} ({patient.weight_kg or 'N/A'} kg)", body_style),
            Paragraph("<b>Review Status:</b>", body_bold),
            Paragraph(f"<b>{prediction.status.upper()}</b>", body_style),
        ],
    ]
    meta_table = Table(meta_data, colWidths=[100, 160, 110, 160])
    meta_table.setStyle(
        TableStyle([
            ("BACKGROUND", (0, 0), (-1, -1), colors.HexColor("#f8fafc")),
            ("BOX", (0, 0), (-1, -1), 0.5, colors.HexColor("#e2e8f0")),
            ("INNERGRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#e2e8f0")),
            ("TOPPADDING", (0, 0), (-1, -1), 5),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
            ("LEFTPADDING", (0, 0), (-1, -1), 6),
            ("RIGHTPADDING", (0, 0), (-1, -1), 6),
        ])
    )
    elements.append(meta_table)
    elements.append(Spacer(1, 14))

    # 3. AI Risk Assessment & Findings Box
    risk_colors = {
        "low": ("#10b981", "#ecfdf5"),
        "moderate": ("#f59e0b", "#fffbeb"),
        "high": ("#ef4444", "#fef2f2"),
        "critical": ("#b91c1c", "#fef2f2"),
    }
    r_color_hex, r_bg_hex = risk_colors.get(prediction.risk_level.lower(), ("#0f766e", "#f0fdfa"))

    risk_style = ParagraphStyle(
        "RiskStyle",
        parent=styles["Normal"],
        fontName="Helvetica-Bold",
        fontSize=14,
        textColor=colors.HexColor(r_color_hex),
    )

    finding_table_data = [
        [
            Paragraph(f"<b>Primary AI Indication:</b> {prediction.possible_disease}", body_bold),
            Paragraph(f"Risk Level: <b>{prediction.risk_level.upper()}</b>", risk_style),
        ],
        [
            Paragraph(f"<b>Model Confidence:</b> {prediction.confidence:.1f}% · <b>Urgency:</b> {str(prediction.urgency).capitalize()}", body_style),
            Paragraph(f"<b>Recommended Specialist:</b> {prediction.recommended_specialist or 'General Physician'}", body_style),
        ]
    ]
    finding_table = Table(finding_table_data, colWidths=[310, 220])
    finding_table.setStyle(
        TableStyle([
            ("BACKGROUND", (0, 0), (-1, -1), colors.HexColor(r_bg_hex)),
            ("BOX", (0, 0), (-1, -1), 1, colors.HexColor(r_color_hex)),
            ("TOPPADDING", (0, 0), (-1, -1), 8),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 8),
            ("LEFTPADDING", (0, 0), (-1, -1), 10),
            ("RIGHTPADDING", (0, 0), (-1, -1), 10),
        ])
    )
    elements.append(finding_table)
    elements.append(Spacer(1, 14))

    # 4. Clinical Symptoms & Reported Vitals Table
    elements.append(Paragraph("Reported Symptoms & Biomarkers", section_heading))

    symptoms_text = ", ".join([s.replace("_", " ").title() for s in (prediction.symptoms_list or [])]) or "None recorded"
    
    vitals_summary = (
        f"BP: {prediction.systolic_bp or '--'}/{prediction.diastolic_bp or '--'} mmHg | "
        f"Heart Rate: {prediction.heart_rate or '--'} bpm | "
        f"SpO2: {prediction.oxygen_level or '--'}% | "
        f"Temp: {prediction.body_temperature or '--'} °C | "
        f"Sugar: {prediction.blood_sugar or '--'} mg/dL"
    )

    vitals_table_data = [
        [Paragraph("<b>Active Symptoms:</b>", body_bold), Paragraph(symptoms_text, body_style)],
    ]
    if getattr(prediction, "other_symptoms", None):
        vitals_table_data.append(
            [Paragraph("<b>Other Symptoms:</b>", body_bold), Paragraph(prediction.other_symptoms, body_style)]
        )
    vitals_table_data.extend([
        [Paragraph("<b>Recorded Vitals:</b>", body_bold), Paragraph(vitals_summary, body_style)],
        [Paragraph("<b>Lifestyle Profile:</b>", body_bold), Paragraph(f"Smoking: {prediction.smoking_status or 'Non-smoker'} | Alcohol: {prediction.alcohol_consumption or 'None'} | Exercise: {prediction.exercise_frequency or 'Sedentary'}", body_style)],
    ])
    vitals_table = Table(vitals_table_data, colWidths=[120, 410])
    vitals_table.setStyle(
        TableStyle([
            ("BOX", (0, 0), (-1, -1), 0.5, colors.HexColor("#cbd5e1")),
            ("INNERGRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#e2e8f0")),
            ("TOPPADDING", (0, 0), (-1, -1), 5),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
            ("LEFTPADDING", (0, 0), (-1, -1), 6),
        ])
    )
    elements.append(vitals_table)
    elements.append(Spacer(1, 12))

    # 5. Tailored Health Guidance & Next Steps
    elements.append(Paragraph("AI Recommendations & Health Suggestions", section_heading))
    suggestions = prediction.suggestions_list or ["Follow up with your assigned primary care physician."]
    for sug in suggestions:
        elements.append(Paragraph(f"• {sug}", body_style))
        elements.append(Spacer(1, 2))

    elements.append(Spacer(1, 10))

    # 6. Doctor Review & Clinical Notes (if reviewed)
    if prediction.doctor_notes or prediction.recommended_medicines or prediction.recommended_tests:
        elements.append(Paragraph("Attending Doctor Clinical Evaluation", section_heading))
        doc_data = []
        if prediction.doctor_notes:
            doc_data.append([Paragraph("<b>Doctor Notes:</b>", body_bold), Paragraph(prediction.doctor_notes, body_style)])
        if prediction.recommended_medicines:
            doc_data.append([Paragraph("<b>Prescriptions:</b>", body_bold), Paragraph(prediction.recommended_medicines, body_style)])
        if prediction.recommended_tests:
            doc_data.append([Paragraph("<b>Diagnostic Tests:</b>", body_bold), Paragraph(prediction.recommended_tests, body_style)])
        
        doc_table = Table(doc_data, colWidths=[120, 410])
        doc_table.setStyle(
            TableStyle([
                ("BACKGROUND", (0, 0), (-1, -1), colors.HexColor("#f0fdf4")),
                ("BOX", (0, 0), (-1, -1), 0.5, colors.HexColor("#86efac")),
                ("INNERGRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#bbf7d0")),
                ("TOPPADDING", (0, 0), (-1, -1), 5),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
                ("LEFTPADDING", (0, 0), (-1, -1), 6),
            ])
        )
        elements.append(doc_table)
        elements.append(Spacer(1, 12))

    # 7. Disclaimer Footer
    elements.append(Spacer(1, 14))
    elements.append(HRFlowable(width="100%", thickness=0.5, color=colors.HexColor("#cbd5e1"), spaceAfter=8))
    elements.append(
        Paragraph(
            "<b>Disclaimer:</b> This document is generated by HealthAI clinical decision support engine for screening and triage purposes only. "
            "It is not a final medical diagnosis. Always consult a certified healthcare professional for medical emergencies.",
            disclaimer_style,
        )
    )

    doc.build(elements)
    buffer.seek(0)
    return buffer.getvalue()

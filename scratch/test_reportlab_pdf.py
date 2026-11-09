import io
from reportlab.lib.pagesizes import letter, A4
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, HRFlowable
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib import colors

buf = io.BytesIO()
doc = SimpleDocTemplate(buf, pagesize=A4, rightMargin=36, leftMargin=36, topMargin=36, bottomMargin=36)
styles = getSampleStyleSheet()

elements = []
elements.append(Paragraph("<b>CITY GENERAL HOSPITAL</b>", styles["Title"]))
elements.append(Paragraph("123 Health Ave, Bangalore | Ph: +91 80 1234 5678", styles["Normal"]))
elements.append(HRFlowable(width="100%", thickness=1, color=colors.HexColor("#0d9488"), spaceBefore=10, spaceAfter=15))

# Table with medicines
data = [
    ["#", "Medicine", "Dosage", "Timing (M-A-E-N)", "Frequency", "Duration", "Instructions"],
    ["1", "Paracetamol 500mg\n(Tablet)", "1 Tab", "M: [X] A: [X] E: [ ] N: [ ]", "Twice Daily", "5 Days", "After food"],
    ["2", "Cetirizine 10mg\n(Tablet)", "1 Tab", "M: [ ] A: [ ] E: [ ] N: [X]", "Once Daily", "3 Days", "At bedtime"]
]

t = Table(data, colWidths=[20, 110, 50, 100, 70, 50, 120])
t.setStyle(TableStyle([
    ('BACKGROUND', (0,0), (-1,0), colors.HexColor("#f0fdfa")),
    ('TEXTCOLOR', (0,0), (-1,0), colors.HexColor("#0f766e")),
    ('FONTNAME', (0,0), (-1,0), 'Helvetica-Bold'),
    ('FONTSIZE', (0,0), (-1,-1), 9),
    ('GRID', (0,0), (-1,-1), 0.5, colors.HexColor("#cbd5e1")),
    ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
]))
elements.append(t)

doc.build(elements)
pdf_bytes = buf.getvalue()
print("Generated PDF size:", len(pdf_bytes), "bytes")

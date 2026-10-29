"""PDF export with wrapped paragraphs, page numbers and escaped user text."""
from io import BytesIO
from pathlib import Path
from xml.sax.saxutils import escape
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.lib.enums import TA_LEFT
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, PageBreak
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont


def pdf_export(session, include_answers=True, include_practice=False):
    # Use a packaged Unicode font when available on the host.
    font = 'Helvetica'
    for p in (Path(__file__).parent/'assets'/'DejaVuSans.ttf', Path('/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf')):
        if p.exists():
            if 'Studio' not in pdfmetrics.getRegisteredFontNames():
                pdfmetrics.registerFont(TTFont('Studio', str(p)))
            font = 'Studio'; break
    out = BytesIO()
    styles = getSampleStyleSheet()
    for s in styles.byName.values():
        s.fontName = font
        s.wordWrap = 'CJK'
    for name in ('Heading1', 'Heading2', 'Heading3'):
        styles[name].keepWithNext = True
    styles['BodyText'].fontSize = 10
    styles['BodyText'].leading = 15
    styles['Heading1'].textColor = colors.HexColor('#16334b')
    story = []
    def para(text, style='BodyText'):
        story.append(Paragraph(escape(str(text)).replace('\n', '<br/>'), styles[style]))
        gap = Spacer(1, 5)
        gap.keepWithNext = style.startswith('Heading')
        story.append(gap)
    pack = session['pack']
    para('INTERVIEW STUDIO', 'Title')
    para(pack['title'], 'Heading1')
    para(f"{session['request']['role']} | {session['request']['experience']} | {len(pack['questions'])} questions")
    para('AI-generated practice material. Review accuracy. Scores are advisory, not hiring decisions.')
    para(pack['role_summary'])
    for a in pack['assumptions']:
        para('Assumption: ' + a)
    for i, q in enumerate(pack['questions']):
        story.append(PageBreak())
        para(f"Question {i+1} - {q['competency']}", 'Heading1')
        para(f"{q['kind']} | {q['difficulty']} | {q['minutes']} minutes")
        para(q['question'], 'Heading2')
        if include_answers:
            para('Expected answer / evidence', 'Heading2'); para(q['expected_answer'])
            para('Follow-up probes', 'Heading2')
            for f in q['follow_ups']: para('- ' + f)
            para('Scoring rubric - 10 points', 'Heading2')
            for c in q['rubric']:
                para(f"{c['name']} ({c['points']} points)", 'Heading3')
                for name, field in [('Zero credit','zero'), ('Partial credit','partial'), ('Full credit','full')]:
                    para(name + ': ' + c[field])
        if include_practice:
            answer = session['answers'].get(str(i), '')
            if answer: para('Your saved answer', 'Heading2'); para(answer)
            f = session['feedback'].get(str(i))
            if f:
                para(f"AI feedback - {sum(c['score'] for c in f['criteria'])}/10 (advisory)", 'Heading2')
                para(f['summary'])
                for c in sorted(f['criteria'], key=lambda c: c['criterion_index']):
                    name = q['rubric'][c['criterion_index']]['name']
                    para(f"{name}: {c['score']} points. Evidence: {c['evidence_quote'] or 'None'}. {c['explanation']}")
                for label, field in [('Strengths','strengths'), ('Missing points','missing_points'), ('Next steps','improvement_plan')]:
                    para(label, 'Heading3')
                    for item in f[field]: para('- ' + item)
                para('Improved answer', 'Heading3'); para(f['improved_answer'])
    def footer(canvas, doc):
        canvas.setFont(font, 8)
        canvas.drawString(42, 25, 'Interview Studio | Practice report')
        canvas.drawRightString(553, 25, str(doc.page))
    SimpleDocTemplate(out, pagesize=(595,842), rightMargin=42,leftMargin=42,
                      topMargin=40,bottomMargin=44, title=pack['title']).build(story, onFirstPage=footer,onLaterPages=footer)
    return out.getvalue()

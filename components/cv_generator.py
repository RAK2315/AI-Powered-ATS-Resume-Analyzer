"""
CV PDF Generator
Creates a clean, ATS-friendly resume PDF using reportlab.
"""

import io
from reportlab.lib.pagesizes import A4
from reportlab.lib.units import mm
from reportlab.lib import colors
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, HRFlowable, Table, TableStyle
)
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.enums import TA_LEFT, TA_CENTER, TA_RIGHT


# ── Color palette (dark accent, clean body) ──────────────────────────────────
ACCENT   = colors.HexColor('#2563EB')   # professional blue
DARK     = colors.HexColor('#111827')   # near-black
MUTED    = colors.HexColor('#6B7280')   # gray
DIVIDER  = colors.HexColor('#E5E7EB')   # light gray line
WHITE    = colors.white


def _styles():
    return {
        'name': ParagraphStyle('name', fontName='Helvetica-Bold',
                               fontSize=22, textColor=DARK,
                               spaceAfter=2, leading=26),
        'tagline': ParagraphStyle('tagline', fontName='Helvetica',
                                  fontSize=11, textColor=MUTED,
                                  spaceAfter=2),
        'contact': ParagraphStyle('contact', fontName='Helvetica',
                                  fontSize=9, textColor=MUTED,
                                  spaceAfter=0, leading=13),
        'section': ParagraphStyle('section', fontName='Helvetica-Bold',
                                  fontSize=10, textColor=ACCENT,
                                  spaceBefore=10, spaceAfter=3,
                                  leading=14, letterSpacing=1),
        'job_title': ParagraphStyle('job_title', fontName='Helvetica-Bold',
                                    fontSize=10, textColor=DARK,
                                    spaceAfter=0, leading=13),
        'job_meta': ParagraphStyle('job_meta', fontName='Helvetica-Oblique',
                                   fontSize=9, textColor=MUTED,
                                   spaceAfter=2, leading=12),
        'bullet': ParagraphStyle('bullet', fontName='Helvetica',
                                 fontSize=9, textColor=DARK,
                                 leftIndent=10, leading=13,
                                 spaceAfter=1, bulletIndent=2),
        'body': ParagraphStyle('body', fontName='Helvetica',
                               fontSize=9, textColor=DARK,
                               leading=13, spaceAfter=2),
        'skill_cat': ParagraphStyle('skill_cat', fontName='Helvetica-Bold',
                                    fontSize=9, textColor=DARK, leading=13),
        'skill_val': ParagraphStyle('skill_val', fontName='Helvetica',
                                    fontSize=9, textColor=DARK, leading=13),
        'edu_title': ParagraphStyle('edu_title', fontName='Helvetica-Bold',
                                    fontSize=10, textColor=DARK,
                                    spaceAfter=0, leading=13),
        'edu_meta': ParagraphStyle('edu_meta', fontName='Helvetica-Oblique',
                                   fontSize=9, textColor=MUTED,
                                   spaceAfter=1, leading=12),
    }


def _section_header(title: str, styles: dict) -> list:
    return [
        Paragraph(title.upper(), styles['section']),
        HRFlowable(width='100%', thickness=0.5, color=DIVIDER, spaceAfter=4),
    ]


def _safe(text: str) -> str:
    """Escape XML special chars for reportlab."""
    return (text or '').replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;')


def generate_resume_pdf(data: dict) -> bytes:
    """
    Generate a PDF resume from structured data dict.

    Expected data keys:
        name, tagline, email, phone, location, linkedin, github,
        summary,
        experiences: [{title, company, location, start, end, bullets: [str]}]
        educations: [{degree, institution, location, start, end, gpa, courses}]
        skills: [{category, items}]
        projects: [{name, tech, bullets: [str], link}]
        certifications: [str]
    """
    buf = io.BytesIO()
    M = 15 * mm

    doc = SimpleDocTemplate(
        buf, pagesize=A4,
        leftMargin=M, rightMargin=M,
        topMargin=12 * mm, bottomMargin=12 * mm,
    )

    S = _styles()
    story = []

    # ── HEADER ────────────────────────────────────────────────────────────────
    name = _safe(data.get('name', ''))
    tagline = _safe(data.get('tagline', ''))

    contact_parts = []
    for key, label in [('email','Email:'), ('phone','Phone:'), ('location','Location:'),
                       ('linkedin','LinkedIn:'), ('github','GitHub:')]:
        val = data.get(key, '').strip()
        if val:
            contact_parts.append(f"{label} {_safe(val)}")

    story.append(Paragraph(name, S['name']))
    if tagline:
        story.append(Paragraph(tagline, S['tagline']))
    if contact_parts:
        story.append(Paragraph('  ·  '.join(contact_parts), S['contact']))

    story.append(Spacer(1, 4))
    story.append(HRFlowable(width='100%', thickness=1.5, color=ACCENT, spaceAfter=6))

    # ── SUMMARY ───────────────────────────────────────────────────────────────
    summary = data.get('summary', '').strip()
    if summary:
        story += _section_header('Professional Summary', S)
        story.append(Paragraph(_safe(summary), S['body']))

    # ── EXPERIENCE ────────────────────────────────────────────────────────────
    experiences = data.get('experiences', [])
    if experiences:
        story += _section_header('Work Experience', S)
        for exp in experiences:
            if not exp.get('title') and not exp.get('company'):
                continue
            title = _safe(exp.get('title', ''))
            company = _safe(exp.get('company', ''))
            loc = _safe(exp.get('location', ''))
            start = _safe(exp.get('start', ''))
            end = _safe(exp.get('end', 'Present'))
            date_str = f"{start} – {end}" if start else end

            # Title + date on same line
            t_data = [[Paragraph(f"<b>{title}</b>", S['job_title']),
                       Paragraph(date_str, ParagraphStyle('r', fontName='Helvetica',
                                 fontSize=9, textColor=MUTED, alignment=TA_RIGHT))]]
            t = Table(t_data, colWidths=[None, 38*mm])
            t.setStyle(TableStyle([('VALIGN', (0,0), (-1,-1), 'TOP'),
                                   ('LEFTPADDING', (0,0), (-1,-1), 0),
                                   ('RIGHTPADDING', (0,0), (-1,-1), 0),
                                   ('TOPPADDING', (0,0), (-1,-1), 0),
                                   ('BOTTOMPADDING', (0,0), (-1,-1), 1)]))
            story.append(t)

            company_loc = f"{company}" + (f", {loc}" if loc else '')
            story.append(Paragraph(company_loc, S['job_meta']))

            for b in exp.get('bullets', []):
                b = b.strip()
                if b:
                    story.append(Paragraph(f"- {_safe(b)}", S['bullet']))
            story.append(Spacer(1, 4))

    # ── PROJECTS ──────────────────────────────────────────────────────────────
    projects = data.get('projects', [])
    if projects:
        story += _section_header('Projects', S)
        for proj in projects:
            if not proj.get('name'):
                continue
            pname = _safe(proj.get('name', ''))
            tech = _safe(proj.get('tech', ''))
            link = _safe(proj.get('link', ''))
            header = f"<b>{pname}</b>"
            if tech:
                header += f" <font color='#6B7280'>| {tech}</font>"
            story.append(Paragraph(header, S['job_title']))
            for b in proj.get('bullets', []):
                b = b.strip()
                if b:
                    story.append(Paragraph(f"- {_safe(b)}", S['bullet']))
            if link:
                story.append(Paragraph(
                    f"<font color='#2563EB'>{link}</font>", S['bullet']))
            story.append(Spacer(1, 4))

    # ── SKILLS ────────────────────────────────────────────────────────────────
    skills = data.get('skills', [])
    if skills:
        story += _section_header('Skills', S)
        skill_rows = []
        for s in skills:
            cat = _safe(s.get('category', ''))
            items = _safe(s.get('items', ''))
            if cat and items:
                skill_rows.append([
                    Paragraph(cat + ':', S['skill_cat']),
                    Paragraph(items, S['skill_val']),
                ])
        if skill_rows:
            # Auto-size category column based on longest category name
            max_cat_len = max(len(s.get('category','')) for s in skills if s.get('category')) if skills else 10
            cat_col_w = min(max(max_cat_len * 1.8 * mm, 35*mm), 55*mm)
            t = Table(skill_rows, colWidths=[cat_col_w, None])
            t.setStyle(TableStyle([
                ('VALIGN', (0,0), (-1,-1), 'TOP'),
                ('LEFTPADDING', (0,0), (-1,-1), 0),
                ('RIGHTPADDING', (0,0), (-1,-1), 6),
                ('TOPPADDING', (0,0), (-1,-1), 2),
                ('BOTTOMPADDING', (0,0), (-1,-1), 2),
            ]))
            story.append(t)

    # ── EDUCATION ─────────────────────────────────────────────────────────────
    educations = data.get('educations', [])
    if educations:
        story += _section_header('Education', S)
        for edu in educations:
            if not edu.get('degree') and not edu.get('institution'):
                continue
            deg = _safe(edu.get('degree', ''))
            inst = _safe(edu.get('institution', ''))
            loc = _safe(edu.get('location', ''))
            start = _safe(edu.get('start', ''))
            end = _safe(edu.get('end', ''))
            gpa = _safe(edu.get('gpa', ''))
            courses = _safe(edu.get('courses', ''))
            date_str = f"{start} – {end}" if start and end else end or start

            t_data = [[Paragraph(f"<b>{deg}</b>", S['edu_title']),
                       Paragraph(date_str, ParagraphStyle('r2', fontName='Helvetica',
                                 fontSize=9, textColor=MUTED, alignment=TA_RIGHT))]]
            t = Table(t_data, colWidths=[None, 38*mm])
            t.setStyle(TableStyle([('VALIGN', (0,0),(-1,-1),'TOP'),
                                   ('LEFTPADDING',(0,0),(-1,-1),0),
                                   ('RIGHTPADDING',(0,0),(-1,-1),0),
                                   ('TOPPADDING',(0,0),(-1,-1),0),
                                   ('BOTTOMPADDING',(0,0),(-1,-1),1)]))
            story.append(t)

            inst_loc = inst + (f", {loc}" if loc else '')
            meta_parts = [inst_loc]
            if gpa:
                meta_parts.append(f"GPA/CGPA: {gpa}")
            story.append(Paragraph(' · '.join(meta_parts), S['edu_meta']))
            if courses:
                story.append(Paragraph(
                    f"Relevant Coursework: {courses}", S['body']))
            story.append(Spacer(1, 4))

    # ── CERTIFICATIONS ────────────────────────────────────────────────────────
    certs = data.get('certifications', [])
    certs = [c for c in certs if c.strip()]
    if certs:
        story += _section_header('Certifications', S)
        for c in certs:
            story.append(Paragraph(f"- {_safe(c)}", S['bullet']))

    doc.build(story)
    buf.seek(0)
    return buf.read()

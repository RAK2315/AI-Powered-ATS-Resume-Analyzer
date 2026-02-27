"""
Resume Structure Extractor v3
Handles messy PDF text where bullets aren't separated by blank lines.
"""

import re
from dataclasses import dataclass, field
from typing import List, Optional


@dataclass
class ParsedResume:
    name: str = ""
    tagline: str = ""
    email: str = ""
    phone: str = ""
    location: str = ""
    linkedin: str = ""
    github: str = ""
    summary: str = ""
    experiences: List[dict] = field(default_factory=list)
    projects: List[dict] = field(default_factory=list)
    skills: List[dict] = field(default_factory=list)
    educations: List[dict] = field(default_factory=list)
    certifications: List[str] = field(default_factory=list)


SECTION_HEADERS = re.compile(
    r'^(PROFILE|SUMMARY|ABOUT(?:\s+ME)?|OBJECTIVE|'
    r'EDUCATION|ACADEMIC|'
    r'SKILLS?|TECHNICAL\s+SKILLS?|'
    r'EXPERIENCE|WORK\s+EXPERIENCE|EMPLOYMENT|'
    r'PROJECTS?|PERSONAL\s+PROJECTS?|'
    r'CERTIFICATIONS?|COURSES?|TRAINING|'
    r'AWARDS?|ACHIEVEMENTS?|HONORS?|PUBLICATIONS?|'
    r'LANGUAGES?|INTERESTS?|ACTIVITIES?)\s*$',
    re.IGNORECASE
)


def extract_resume_structure(text: str, gemini_model=None) -> ParsedResume:
    if gemini_model:
        result = _extract_with_gemini(text, gemini_model)
        if result and result.name:
            return result
    return _extract_with_regex(text)


def _extract_with_gemini(text: str, model) -> Optional[ParsedResume]:
    import json

    prompt = f"""Parse this resume into structured JSON. Extract ALL content accurately.

RESUME TEXT:
{text[:4500]}

Return ONLY valid JSON (no markdown, no backticks):
{{
  "name": "full name from top of resume",
  "tagline": "professional title line (e.g. 'Computer Science Student | Aspiring ML Engineer')",
  "email": "email address",
  "phone": "phone number as string",
  "location": "city, state/country",
  "linkedin": "full linkedin url",
  "github": "github url or empty string",
  "summary": "complete profile/summary paragraph verbatim",
  "experiences": [],
  "projects": [
    {{
      "name": "project name WITHOUT dates (e.g. 'AI Voice Detection API' not 'AI Voice Detection API, 01/2025')",
      "tech": "from the Technologies: line within this project",
      "link": "github/demo link or empty string",
      "start": "start date",
      "end": "end date",
      "bullets": [
        "each bullet point as a complete sentence",
        "combine wrapped lines into single strings"
      ]
    }}
  ],
  "skills": [
    {{"category": "exact category from resume e.g. 'Programming Languages'", "items": "exact items e.g. 'Python, C, C++'"}}
  ],
  "educations": [
    {{
      "degree": "degree name e.g. 'Bachelor of Technology in Computer Science Engineering (AI & ML)'",
      "institution": "university name e.g. 'JSS University'",
      "location": "city",
      "start": "start date",
      "end": "end date or Present",
      "gpa": "gpa/cgpa/percentage or empty string",
      "courses": "relevant coursework as comma-separated string"
    }}
  ],
  "certifications": ["only actual certifications/courses, NOT awards"]
}}

Rules:
1. Extract ALL projects (there are multiple in this resume)
2. Each project bullet: combine wrapped lines into ONE complete sentence
3. Technologies line → goes into "tech" field, NOT bullets
4. Skills: use EXACT category names and items from the resume
5. Awards/Achievements section: do NOT put in certifications array — leave certifications as []
6. If no github in resume, put empty string"""

    try:
        resp = model.generate_content(prompt)
        raw = resp.text.strip()
        # Strip markdown code fences
        raw = re.sub(r'^```(?:json)?\s*\n?', '', raw)
        raw = re.sub(r'\n?```\s*$', '', raw)
        raw = raw.strip()
        data = json.loads(raw)
        return ParsedResume(**{k: data.get(k, v)
                               for k, v in ParsedResume().__dict__.items()})
    except Exception as e:
        print(f"Gemini parse error: {e}")
        return None


def _extract_with_regex(text: str) -> ParsedResume:
    result = ParsedResume()
    lines = [l.rstrip() for l in text.split('\n')]

    # ── contact ───────────────────────────────────────────────────────────────
    em = re.search(r'[\w.+-]+@[\w.-]+\.[a-z]{2,}', text)
    if em: result.email = em.group(0)

    ph = re.search(r'\+?[\d][\d\s\-().]{7,15}[\d]', text)
    if ph: result.phone = re.sub(r'\s+', ' ', ph.group(0)).strip()

    li = re.search(r'linkedin\.com/in/[\w\-]+', text, re.I)
    if li: result.linkedin = li.group(0)

    gh = re.search(r'github\.com/[\w\-]+(?!/[\w])', text, re.I)
    if gh: result.github = gh.group(0)

    # Name & tagline from top lines
    for i, line in enumerate(lines[:5]):
        l = line.strip()
        if l and len(l.split()) <= 6 and not re.search(r'[@\d|]', l) and not result.name:
            result.name = l
        elif (l and result.name and len(l) < 80
              and not re.search(r'@|\+\d|\d{8,}', l)
              and 'linkedin' not in l.lower() and not result.tagline):
            result.tagline = l

    # ── split into labelled sections ──────────────────────────────────────────
    sections = {}
    current_key = None
    current_lines = []

    for line in lines:
        stripped = line.strip()
        if SECTION_HEADERS.match(stripped):
            if current_key is not None:
                sections.setdefault(current_key, []).extend(current_lines)
            # Normalize key
            key = stripped.upper().split()[0]
            key = {'PROFILE': 'SUMMARY', 'ABOUT': 'SUMMARY', 'WORK': 'EXPERIENCE',
                   'EMPLOYMENT': 'EXPERIENCE', 'PERSONAL': 'PROJECTS',
                   'TECHNICAL': 'SKILLS', 'COURSE': 'CERTIFICATIONS',
                   'TRAINING': 'CERTIFICATIONS', 'AWARD': 'AWARDS',
                   'ACHIEVEMENT': 'AWARDS', 'HONOR': 'AWARDS'}.get(key, key)
            current_key = key
            current_lines = []
        elif current_key is not None:
            current_lines.append(line)

    if current_key is not None:
        sections.setdefault(current_key, []).extend(current_lines)

    # ── parse each section ────────────────────────────────────────────────────
    if 'SUMMARY' in sections:
        result.summary = ' '.join(l.strip() for l in sections['SUMMARY'] if l.strip())

    if 'SKILLS' in sections:
        result.skills = _parse_skills(sections['SKILLS'])

    if 'EDUCATION' in sections:
        result.educations = _parse_education(sections['EDUCATION'])

    if 'EXPERIENCE' in sections:
        result.experiences = _parse_experience(sections['EXPERIENCE'])

    if 'PROJECTS' in sections:
        result.projects = _parse_projects(sections['PROJECTS'])

    if 'CERTIFICATIONS' in sections:
        result.certifications = _parse_certs(sections['CERTIFICATIONS'])

    # Awards: single merged entry, not split into certifications
    if 'AWARDS' in sections:
        award_lines = [l.strip() for l in sections['AWARDS'] if l.strip()]
        if award_lines:
            # Merge into single award entry
            merged = _merge_award_lines(award_lines)
            result.certifications.extend(merged)

    return result


def _parse_skills(lines: list) -> list:
    skills = []
    for line in lines:
        l = line.strip()
        if not l:
            continue
        m = re.match(r'^([^:]{2,50}):\s*(.+)$', l)
        if m:
            skills.append({'category': m.group(1).strip(), 'items': m.group(2).strip()})
    return skills


def _parse_education(lines: list) -> list:
    edu = {'degree': '', 'institution': '', 'location': '',
           'start': '', 'end': '', 'gpa': '', 'courses': ''}
    course_buffer = []
    capturing_courses = False

    for i, line in enumerate(lines):
        l = line.strip()
        if not l:
            continue

        if any(kw in l.lower() for kw in ['bachelor','b.tech','master','m.tech','phd','b.e','mba','b.sc','bachelor']):
            # Strip trailing dates
            dm = re.search(r'\s+\d{2}/\d{4}.*$', l)
            if dm:
                date_part = l[dm.start():]
                l = l[:dm.start()].strip()
                dr = re.search(r'(\d{2}/\d{4})\s+[-–]\s*(\S+)', date_part)
                if dr:
                    edu['start'] = dr.group(1)
                    edu['end']   = dr.group(2)
            # Split institution
            if ',' in l:
                parts = l.rsplit(',', 1)
                edu['degree']      = parts[0].strip()
                edu['institution'] = parts[1].strip()
            else:
                edu['degree'] = l

        elif re.match(r'^\d{2}/\d{4}', l):
            dr = re.search(r'(\d{2}/\d{4})\s+[-–]\s*(\S+)', l)
            if dr:
                edu['start'] = dr.group(1)
                edu['end']   = dr.group(2)
            loc_m = re.search(r'\b([A-Z][a-z]{2,}(?:,\s*[A-Z][a-z]+)?)\s*$', l)
            if loc_m:
                edu['location'] = loc_m.group(1)

        elif re.search(r'coursework', l, re.I):
            capturing_courses = True
            c = re.sub(r'.*?coursework[:\s]*', '', l, flags=re.I).strip().lstrip('•– ')
            if c:
                course_buffer.append(c)

        elif capturing_courses:
            if l.startswith(('•', '-')) or (l and l[0].islower()):
                course_buffer.append(l.lstrip('•-– '))
            else:
                capturing_courses = False

        elif re.search(r'\bgpa\b|\bcgpa\b|%', l, re.I):
            gm = re.search(r'[\d.]+\s*/\s*[\d.]+|[\d.]+\s*%', l)
            if gm: edu['gpa'] = gm.group(0)

        elif not edu['location'] and re.match(r'^[A-Z][a-z]+(?:,\s*[A-Z][a-z]+)?$', l):
            edu['location'] = l

    if course_buffer:
        edu['courses'] = ' '.join(course_buffer)

    return [edu] if (edu['degree'] or edu['institution']) else []


def _parse_experience(lines: list) -> list:
    entries = []
    current = None

    for line in lines:
        l = line.strip()
        if not l:
            if current:
                entries.append(current)
                current = None
            continue

        is_bullet = l.startswith(('•', '-', '*', '–', '·'))
        is_tech   = re.match(r'^Technologies?:', l, re.I)

        if is_bullet or is_tech:
            if current:
                b = l.lstrip('•-*–· ')
                if is_tech:
                    current['tech'] = re.sub(r'^Technologies?:\s*', '', l, flags=re.I)
                elif len(b) > 5:
                    current['bullets'].append(b)
        elif current is None:
            current = {'title': l, 'company': '', 'location': '',
                       'start': '', 'end': 'Present', 'bullets': []}
            dm = re.search(r'(\w+[\s/]\d{4})\s*[-–]\s*(\w+[\s/]\d{4}|present)', l, re.I)
            if dm:
                current['start'] = dm.group(1)
                current['end']   = dm.group(2)
        elif current and not current['company']:
            current['company'] = l

    if current:
        entries.append(current)
    return entries[:4]


def _parse_projects(lines: list) -> list:
    """
    Parse projects handling multiple formats:
    - Plain text lines (no bullets) between project headers
    - Bullet lines starting with •, -, etc.
    - Technologies: line at end of each project
    - Date-only lines
    - Subtitle lines with |
    
    New project detected by: line with date pattern OR line that is short/title-like
    after a Technologies: line.
    """
    entries = []
    current = None
    last_was_tech = False

    def _is_project_header(line: str) -> bool:
        """A line is a new project header if it looks like a title (not a sentence)."""
        l = line.strip()
        if not l or l.startswith(('•', '-', '–', '*')):
            return False
        if re.match(r'^Technologies?:', l, re.I):
            return False
        # Has a date → likely a header
        if re.search(r'\d{2}/\d{4}', l):
            return True
        # Very long sentence-like lines are NOT headers
        if len(l) > 120:
            return False
        # Lines ending with period are body text
        if l.endswith('.'):
            return False
        # Lines ending with comma are wrapped mid-sentence
        if l.endswith(','):
            return False
        # Lines with lots of lowercase words mid-sentence are body text
        words = l.split()
        if len(words) > 6 and sum(1 for w in words[1:] if w[0].islower()) > 3:
            return False
        return True

    for line in lines:
        l = line.strip()
        if not l:
            continue

        is_bullet   = l.startswith(('•', '-', '–', '*', '·'))
        is_tech     = bool(re.match(r'^Technologies?:', l, re.I))
        is_date_only= bool(re.match(r'^\d{2}/\d{4}\s*[-–]', l))
        is_subtitle = ('|' in l and len(l) < 120 and not is_bullet
                       and current is not None and not is_tech)
        # Continuation: starts lowercase OR starts with connecting words
        is_continuation = (current is not None and not is_bullet and not is_tech
                          and not is_date_only and not is_subtitle
                          and l and (l[0].islower()
                                     or l[:6].lower() in ('with r', 'with s', 'with a', 'throug', 'across', 'indian', 'soft v', 'achiev', 'design', 'deplo')))

        if is_date_only:
            if current:
                dm = re.search(r'(\d{2}/\d{4})\s*[-–]\s*(\d{2}/\d{4}|\w+)', l)
                if dm:
                    current['start'] = dm.group(1)
                    current['end']   = dm.group(2)
            last_was_tech = False

        elif is_tech:
            if current:
                current['tech'] = re.sub(r'^Technologies?:\s*', '', l, flags=re.I).strip()
            last_was_tech = True

        elif is_subtitle:
            last_was_tech = False

        elif is_bullet:
            if current is None:
                current = {'name':'','tech':'','link':'','start':'','end':'','bullets':[]}
            b = l.lstrip('•-–*· ').strip()
            if b:
                current['bullets'].append(b)
            last_was_tech = False

        elif is_continuation and not last_was_tech:
            if current and current['bullets']:
                current['bullets'][-1] += ' ' + l
            elif current:
                current['bullets'].append(l)
            last_was_tech = False

        elif last_was_tech or (current is not None and _is_project_header(l)):
            # New project
            if current and current['name']:
                entries.append(current)
            clean = re.sub(r',?\s*\d{2}/\d{4}.*$', '', l).strip().rstrip(',').strip()
            current = {'name': clean, 'tech': '', 'link': '', 'start': '', 'end': '', 'bullets': []}
            dm = re.search(r'(\d{2}/\d{4})\s*[-–]\s*(\d{2}/\d{4}|\w+)', l)
            if dm:
                current['start'] = dm.group(1)
                current['end']   = dm.group(2)
            last_was_tech = False

        elif current is None and _is_project_header(l):
            clean = re.sub(r',?\s*\d{2}/\d{4}.*$', '', l).strip().rstrip(',').strip()
            current = {'name': clean, 'tech': '', 'link': '', 'start': '', 'end': '', 'bullets': []}
            dm = re.search(r'(\d{2}/\d{4})\s*[-–]\s*(\d{2}/\d{4}|\w+)', l)
            if dm:
                current['start'] = dm.group(1)
                current['end']   = dm.group(2)
            last_was_tech = False

        else:
            # Plain text content line — add as bullet
            if current is not None:
                if len(l) > 10:
                    current['bullets'].append(l)
            last_was_tech = False

    if current and current['name']:
        entries.append(current)

    return entries


def _parse_certs(lines: list) -> list:
    certs = []
    buf = ''
    for line in lines:
        l = line.strip().lstrip('•-– ')
        if not l:
            continue
        # New entry if line has a year or starts with capital
        has_year = bool(re.search(r'\b20\d{2}\b', l))
        if not buf:
            buf = l
        elif has_year and len(buf) > 20:
            certs.append(buf)
            buf = l
        else:
            buf += ' ' + l
    if buf:
        certs.append(buf)
    return certs


def _merge_award_lines(lines: list) -> list:
    """Merge multi-line award into one entry."""
    return [' '.join(lines)]

"""
Section Evaluator Component
Analyzes and scores individual resume sections.
"""

import re
from dataclasses import dataclass, field
from typing import Dict, List, Optional


@dataclass
class Section:
    name: str
    content: str
    start_idx: int
    end_idx: int


@dataclass
class SectionScore:
    section_name: str
    score: int  # 0-100
    present: bool
    completeness: float
    relevance: float
    feedback: str
    improvement_areas: List[str] = field(default_factory=list)


@dataclass
class CompletenessReport:
    total_score: int
    present_sections: List[str]
    missing_sections: List[str]
    section_scores: Dict[str, SectionScore]
    overall_feedback: str


# Section detection patterns
SECTION_PATTERNS = {
    'contact': [
        r'contact\s*(information|info|details)?',
        r'personal\s*(information|info|details)?',
        r'(phone|email|address|linkedin|github)',
    ],
    'summary': [
        r'(professional\s*)?(summary|profile|objective|overview|about)',
        r'career\s*(objective|summary|goal)',
    ],
    'skills': [
        r'(technical\s*)?(skills?|competencies|expertise|technologies)',
        r'(core\s*)?competencies',
        r'tools?\s*(and\s*technologies)?',
    ],
    'experience': [
        r'(work|professional|relevant)?\s*(experience|history|background)',
        r'employment\s*(history|record)?',
        r'(internship|internships)',
        r'positions?\s*held',
    ],
    'education': [
        r'education(al)?\s*(background|qualifications?)?',
        r'academic\s*(background|qualifications?|history)?',
        r'(degrees?|qualifications?)',
        r'university|college|school',
    ],
    'projects': [
        r'(personal\s*|academic\s*|key\s*)?(projects?|portfolio)',
        r'(notable|relevant)\s*projects?',
    ],
    'certifications': [
        r'certifications?\s*(and\s*licenses?)?',
        r'licenses?\s*(and\s*certifications?)?',
        r'credentials?|courses?|training',
    ],
    'achievements': [
        r'(awards?|achievements?|accomplishments?|honors?|recognition)',
        r'publications?|presentations?',
    ]
}

REQUIRED_SECTIONS = {'contact', 'skills', 'experience', 'education'}
OPTIONAL_SECTIONS = {'summary', 'projects', 'certifications', 'achievements'}


class SectionEvaluator:
    """Analyzes and scores individual resume sections."""

    def identify_sections(self, resume_text: str) -> Dict[str, Section]:
        """Identify standard resume sections from text."""
        if not resume_text:
            return {}

        lines = resume_text.split('\n')
        identified = {}

        for i, line in enumerate(lines):
            line_clean = line.strip().lower()
            if not line_clean or len(line_clean) > 60:
                continue

            for section_name, patterns in SECTION_PATTERNS.items():
                if section_name in identified:
                    continue
                for pattern in patterns:
                    if re.search(pattern, line_clean, re.IGNORECASE):
                        # Collect content until next section header
                        content_lines = []
                        for j in range(i + 1, min(i + 50, len(lines))):
                            next_line = lines[j].strip().lower()
                            if next_line and self._is_section_header(next_line, section_name):
                                break
                            content_lines.append(lines[j])

                        identified[section_name] = Section(
                            name=section_name,
                            content='\n'.join(content_lines),
                            start_idx=i,
                            end_idx=i + len(content_lines)
                        )
                        break

        # If no sections found, treat full text as one blob and guess
        if not identified:
            identified = self._heuristic_detection(resume_text)

        # Contact info: always check header lines (email/phone/linkedin in first 5 lines)
        # regardless of whether a CONTACT section header exists
        if 'contact' not in identified:
            header_lines = resume_text.split('\n')[:6]
            header_text = '\n'.join(header_lines)
            has_contact = any(
                re.search(pat, header_text, re.IGNORECASE)
                for pat in [r'[\w.+-]+@[\w.-]+\.[a-z]{2,}',
                            r'\+?\d[\d\s\-().]{7,15}\d',
                            r'linkedin\.com',
                            r'github\.com']
            )
            if has_contact:
                identified['contact'] = Section('contact', header_text, 0, 6)

        return identified

    def _is_section_header(self, line: str, current_section: str) -> bool:
        """Check if a line is a different section header.
        
        A true section header is:
        - Short (< 45 chars)
        - Does NOT contain a colon followed by content (e.g. "Skills: Python" is not a header)
        - Does NOT contain typical sentence punctuation suggesting it's body text
        """
        # Skip obvious content lines
        if len(line) > 45:
            return False
        # Skip lines with "word: content" pattern (skill categories, contact fields etc.)
        if re.search(r'\w+\s*:\s*\w', line):
            return False
        # Skip lines that are clearly bullet content
        if line.startswith(('•', '-', '*', '·')):
            return False
        
        for section_name, patterns in SECTION_PATTERNS.items():
            if section_name == current_section:
                continue
            for pattern in patterns:
                if re.search(pattern, line, re.IGNORECASE):
                    return True
        return False

    def _heuristic_detection(self, text: str) -> Dict[str, Section]:
        """Fallback: detect sections by common content patterns."""
        detected = {}
        text_lower = text.lower()

        if re.search(r'\b(email|phone|linkedin|github|@)\b', text_lower):
            detected['contact'] = Section('contact', text[:200], 0, 200)

        if re.search(r'\b(python|java|sql|excel|aws|react)\b', text_lower):
            detected['skills'] = Section('skills', text, 0, len(text))

        if re.search(r'\b(intern|engineer|developer|analyst|manager|worked|responsible)\b', text_lower):
            detected['experience'] = Section('experience', text, 0, len(text))

        if re.search(r'\b(university|college|bachelor|master|degree|b\.tech|m\.tech|bsc|msc)\b', text_lower):
            detected['education'] = Section('education', text, 0, len(text))

        return detected

    def set_full_resume_text(self, text: str):
        """Store full resume text for contact detection."""
        self._full_resume_text = text

    def score_section(self, section: Section, job_desc: str) -> SectionScore:
        """Score a specific section based on completeness and relevance."""
        scorers = {
            'contact': self._score_contact,
            'summary': self._score_summary,
            'skills': self._score_skills,
            'experience': self._score_experience,
            'education': self._score_education,
            'projects': self._score_projects,
            'certifications': self._score_certifications,
            'achievements': self._score_achievements,
        }

        scorer = scorers.get(section.name, self._score_generic)
        return scorer(section, job_desc)

    def evaluate_completeness(self, sections: Dict[str, Section]) -> CompletenessReport:
        """Evaluate overall resume completeness."""
        present = list(sections.keys())
        missing = [s for s in REQUIRED_SECTIONS if s not in sections]

        section_scores = {}
        for name, section in sections.items():
            section_scores[name] = self.score_section(section, "")

        total = int(sum(s.score for s in section_scores.values()) / max(len(section_scores), 1))

        # Penalize for missing required sections
        penalty = len(missing) * 10
        total = max(0, total - penalty)

        feedback_parts = []
        if missing:
            feedback_parts.append(f"Missing critical sections: {', '.join(missing)}.")
        if total >= 80:
            feedback_parts.append("Overall resume structure is strong.")
        elif total >= 60:
            feedback_parts.append("Resume structure is adequate but has room for improvement.")
        else:
            feedback_parts.append("Resume structure needs significant improvement.")

        return CompletenessReport(
            total_score=total,
            present_sections=present,
            missing_sections=missing,
            section_scores=section_scores,
            overall_feedback=' '.join(feedback_parts)
        )

    # --- Section-specific scorers ---

    def _score_contact(self, section: Section, job_desc: str) -> SectionScore:
        # Contact info is usually at the top of the resume, not under a header.
        # So we must search the full resume text stored in _full_resume_text if available,
        # OR fall back to the section content itself.
        search_text = (getattr(self, '_full_resume_text', '') + ' ' + section.content).lower()
        improvements = []
        score = 40  # base

        if re.search(r'[\w.+-]+@[\w.-]+\.[a-z]{2,}', search_text):
            score += 20
        else:
            improvements.append("Add your email address.")

        if re.search(r'\+?\d[\d\s\-().]{7,}', search_text):
            score += 15
        else:
            improvements.append("Add your phone number.")

        if re.search(r'linkedin', search_text):
            score += 15
        else:
            improvements.append("Add your LinkedIn profile URL.")

        if re.search(r'github', search_text):
            score += 10
        else:
            improvements.append("Consider adding your GitHub profile.")

        return SectionScore(
            section_name='Contact Information',
            score=min(score, 100),
            present=True,
            completeness=score / 100,
            relevance=1.0,
            feedback="Contact section present." if score > 60 else "Contact section is incomplete.",
            improvement_areas=improvements
        )

    def _score_summary(self, section: Section, job_desc: str) -> SectionScore:
        content = section.content
        word_count = len(content.split())
        improvements = []
        score = 50

        if word_count >= 30:
            score += 25
        else:
            improvements.append("Expand your summary to at least 3-4 sentences (30+ words).")

        if word_count >= 60:
            score += 15
        elif word_count > 80:
            improvements.append("Summary is too long — keep it concise (under 80 words).")

        if job_desc:
            job_words = set(job_desc.lower().split())
            summary_words = set(content.lower().split())
            overlap = len(job_words & summary_words)
            if overlap > 5:
                score += 10

        return SectionScore(
            section_name='Professional Summary',
            score=min(score, 100),
            present=True,
            completeness=min(word_count / 50, 1.0),
            relevance=0.7,
            feedback="Summary present." if score > 60 else "Summary needs more detail.",
            improvement_areas=improvements
        )

    def _score_skills(self, section: Section, job_desc: str) -> SectionScore:
        content = section.content.lower()
        improvements = []
        score = 30

        # Count distinct skill tokens
        words = re.findall(r'\b[a-z][a-z0-9+#.]{1,20}\b', content)
        unique_skills = len(set(words))

        if unique_skills >= 5:
            score += 20
        else:
            improvements.append("List at least 5-10 relevant skills.")

        if unique_skills >= 10:
            score += 20

        if unique_skills >= 15:
            score += 15

        # Check if organized (has categories)
        if re.search(r'(technical|soft|tools|languages|frameworks)', content):
            score += 15
        else:
            improvements.append("Consider organizing skills into categories (e.g., Technical, Tools, Soft Skills).")

        if job_desc:
            job_words = set(job_desc.lower().split())
            skill_words = set(words)
            overlap = len(job_words & skill_words)
            if overlap > 3:
                score += 10

        return SectionScore(
            section_name='Skills',
            score=min(score, 100),
            present=True,
            completeness=min(unique_skills / 15, 1.0),
            relevance=0.8,
            feedback=f"Found approximately {unique_skills} unique skills.",
            improvement_areas=improvements
        )

    def _score_experience(self, section: Section, job_desc: str) -> SectionScore:
        content = section.content
        improvements = []
        score = 20

        # Check for bullet points / action verbs
        bullet_count = len(re.findall(r'[•\-\*]', content))
        if bullet_count >= 3:
            score += 20
        else:
            improvements.append("Use bullet points to list your responsibilities and achievements.")

        # Check for quantification (numbers, %)
        if re.search(r'\d+%|\$[\d,]+|\d+\s*(users?|customers?|projects?|million|thousand)', content, re.IGNORECASE):
            score += 25
        else:
            improvements.append("Quantify your achievements (e.g., 'Improved performance by 30%', 'Managed team of 5').")

        # Check for action verbs
        action_verbs = ['developed', 'built', 'led', 'managed', 'designed', 'implemented',
                        'improved', 'created', 'delivered', 'achieved', 'increased', 'reduced']
        verbs_found = sum(1 for v in action_verbs if v in content.lower())
        if verbs_found >= 3:
            score += 20
        else:
            improvements.append("Start bullet points with strong action verbs (e.g., Developed, Led, Implemented).")

        # Check for dates
        if re.search(r'\b(20\d{2}|19\d{2}|jan|feb|mar|apr|may|jun|jul|aug|sep|oct|nov|dec)\b', content, re.IGNORECASE):
            score += 15
        else:
            improvements.append("Include dates for each position (month/year format).")

        return SectionScore(
            section_name='Work Experience',
            score=min(score, 100),
            present=True,
            completeness=min(bullet_count / 6, 1.0),
            relevance=0.9,
            feedback="Experience section present." if score > 50 else "Experience section needs improvement.",
            improvement_areas=improvements
        )

    def _score_education(self, section: Section, job_desc: str) -> SectionScore:
        content = section.content.lower()
        improvements = []
        score = 40

        degree_terms = ['bachelor', 'master', 'phd', 'b.tech', 'm.tech', 'bsc', 'msc', 'b.e', 'm.e', 'degree', 'diploma']
        if any(t in content for t in degree_terms):
            score += 25
        else:
            improvements.append("Clearly state your degree (e.g., B.Tech in Computer Science).")

        if re.search(r'(university|college|institute|school)', content):
            score += 20
        else:
            improvements.append("Include your institution name.")

        if re.search(r'(20\d{2}|19\d{2})', content):
            score += 15
        else:
            improvements.append("Add your graduation year.")

        if re.search(r'(cgpa|gpa|percentage|grade)', content):
            score += 10

        return SectionScore(
            section_name='Education',
            score=min(score, 100),
            present=True,
            completeness=score / 100,
            relevance=0.7,
            feedback="Education section present." if score > 60 else "Education section needs more detail.",
            improvement_areas=improvements
        )

    def _score_projects(self, section: Section, job_desc: str) -> SectionScore:
        content = section.content
        improvements = []
        score = 40

        # Count project entries (look for titles / separators)
        project_count = len(re.findall(r'\n[A-Z]', content))
        if project_count >= 2:
            score += 20
        else:
            improvements.append("Include at least 2-3 projects.")

        if re.search(r'(github|gitlab|demo|link|url|http)', content, re.IGNORECASE):
            score += 20
        else:
            improvements.append("Add GitHub links or demo URLs to your projects.")

        if re.search(r'\b(built|developed|created|designed|implemented)\b', content, re.IGNORECASE):
            score += 20
        else:
            improvements.append("Describe what you built and the technologies used.")

        return SectionScore(
            section_name='Projects',
            score=min(score, 100),
            present=True,
            completeness=min(project_count / 3, 1.0),
            relevance=0.8,
            feedback="Projects section present.",
            improvement_areas=improvements
        )

    def _score_certifications(self, section: Section, job_desc: str) -> SectionScore:
        content = section.content
        cert_count = len(re.findall(r'\n', content)) + 1
        return SectionScore(
            section_name='Certifications',
            score=70,
            present=True,
            completeness=min(cert_count / 3, 1.0),
            relevance=0.6,
            feedback="Certifications section present. Include issuing organization and date.",
            improvement_areas=["Add the issuing organization for each certification.", "Include dates obtained."]
        )

    def _score_achievements(self, section: Section, job_desc: str) -> SectionScore:
        return SectionScore(
            section_name='Achievements',
            score=75,
            present=True,
            completeness=0.8,
            relevance=0.6,
            feedback="Achievements section present.",
            improvement_areas=["Quantify achievements where possible."]
        )

    def _score_generic(self, section: Section, job_desc: str) -> SectionScore:
        word_count = len(section.content.split())
        score = min(50 + word_count // 5, 100)
        return SectionScore(
            section_name=section.name.title(),
            score=score,
            present=True,
            completeness=min(word_count / 50, 1.0),
            relevance=0.5,
            feedback=f"{section.name.title()} section detected.",
            improvement_areas=[]
        )

"""
AI Suggester Component
Generates improvement recommendations using Google Gemini (free tier).
"""

import time
from dataclasses import dataclass, field
from typing import List, Optional

try:
    import google.generativeai as genai
    GEMINI_AVAILABLE = True
except ImportError:
    GEMINI_AVAILABLE = False


@dataclass
class Suggestion:
    suggestion: str
    category: str
    impact_estimate: str
    implementation_difficulty: str


@dataclass
class PrioritizedSuggestion:
    suggestion: str
    priority: int  # 1-5, 1 = highest
    category: str
    impact_estimate: str
    implementation_difficulty: str


FALLBACK_SUGGESTIONS = [
    PrioritizedSuggestion(
        suggestion="Add quantifiable achievements to your experience bullets (e.g., 'Improved API response time by 40%').",
        priority=1, category="experience", impact_estimate="High", implementation_difficulty="Medium"
    ),
    PrioritizedSuggestion(
        suggestion="Tailor your skills section to match the exact keywords used in the job description.",
        priority=1, category="keywords", impact_estimate="High", implementation_difficulty="Low"
    ),
    PrioritizedSuggestion(
        suggestion="Add a 2-3 sentence professional summary at the top that mirrors the job requirements.",
        priority=2, category="structure", impact_estimate="High", implementation_difficulty="Low"
    ),
    PrioritizedSuggestion(
        suggestion="Use action verbs at the start of every bullet point (e.g., Developed, Led, Implemented, Designed).",
        priority=2, category="language", impact_estimate="Medium", implementation_difficulty="Low"
    ),
    PrioritizedSuggestion(
        suggestion="Ensure your resume is in a clean, ATS-friendly format — avoid tables, columns, and graphics.",
        priority=3, category="format", impact_estimate="Medium", implementation_difficulty="Low"
    ),
]


class AISuggester:
    """Generates AI-powered resume improvement suggestions using Google Gemini."""

    MAX_RETRIES = 3
    RETRY_DELAY = 2

    def __init__(self, api_key: Optional[str] = None):
        self.api_key = api_key
        self.model = None
        if api_key and GEMINI_AVAILABLE:
            try:
                genai.configure(api_key=api_key)
                self.model = genai.GenerativeModel('gemini-1.5-flash')
            except Exception:
                self.model = None

    def generate_suggestions(self, analysis_context: dict) -> List[PrioritizedSuggestion]:
        """Generate improvement suggestions based on analysis results."""
        if not self.model:
            return FALLBACK_SUGGESTIONS

        prompt = self._build_prompt(analysis_context)

        for attempt in range(self.MAX_RETRIES):
            try:
                response = self.model.generate_content(prompt)
                suggestions = self._parse_suggestions(response.text)
                if suggestions:
                    return suggestions
            except Exception as e:
                if attempt < self.MAX_RETRIES - 1:
                    time.sleep(self.RETRY_DELAY * (attempt + 1))
                continue

        return FALLBACK_SUGGESTIONS

    def generate_content_for_section(self, section_type: str, context: dict) -> str:
        """Generate content for a missing resume section."""
        if not self.model:
            return self._get_template(section_type, context)

        prompt = self._build_content_prompt(section_type, context)

        for attempt in range(self.MAX_RETRIES):
            try:
                response = self.model.generate_content(prompt)
                return response.text.strip()
            except Exception:
                if attempt < self.MAX_RETRIES - 1:
                    time.sleep(self.RETRY_DELAY)
                continue

        return self._get_template(section_type, context)

    def _build_prompt(self, ctx: dict) -> str:
        score = ctx.get('score', 'N/A')
        missing_kws = ctx.get('missing_keywords', [])[:10]
        missing_sections = ctx.get('missing_sections', [])
        job_desc_snippet = ctx.get('job_desc', '')[:500]
        section_issues = ctx.get('section_improvements', [])
        mode = ctx.get('candidate_mode', 'Student / Fresher')

        kw_list = ', '.join(missing_kws) if missing_kws else 'None identified'
        sec_list = ', '.join(missing_sections) if missing_sections else 'None'
        issues_list = '\n'.join(f'- {i}' for i in section_issues[:8]) if section_issues else 'None'

        mode_context = ""
        if "Fresher" in mode or "Student" in mode:
            mode_context = "This is a STUDENT/FRESHER resume. Focus on academic projects, coursework, certifications, and transferable skills. Do NOT suggest adding work experience they don't have."
        elif "Internship" in mode:
            mode_context = "This is an INTERNSHIP applicant. They may have limited experience. Focus on projects, skills, and eagerness to learn."
        else:
            mode_context = "This is an EXPERIENCED PROFESSIONAL. Focus on impact quantification, leadership, and senior-level positioning."

        return f"""You are an expert ATS resume coach. {mode_context}

ANALYSIS RESULTS:
- ATS Compatibility Score: {score}/100
- Missing Keywords: {kw_list}
- Missing Resume Sections: {sec_list}
- Specific Section Issues:
{issues_list}

Job Description (excerpt):
{job_desc_snippet}

Generate exactly 6 specific, actionable improvement suggestions tailored to this candidate's profile.
Format each suggestion EXACTLY like this (no extra text):

SUGGESTION 1:
Text: [specific actionable advice]
Category: [keywords/experience/structure/format/language/skills]
Impact: [High/Medium/Low]
Difficulty: [Low/Medium/High]

SUGGESTION 2:
...and so on up to SUGGESTION 6.

Be specific, practical, and professional. Focus on ATS optimization."""

    def _build_content_prompt(self, section_type: str, ctx: dict) -> str:
        job_desc = ctx.get('job_desc', '')[:800]
        existing = ctx.get('existing_resume', '')[:600]
        role = ctx.get('target_role', 'the target role')
        mode = ctx.get('candidate_mode', 'Student / Fresher')
        is_fresher = 'Fresher' in mode or 'Student' in mode or 'Internship' in mode
        ctype = 'Student/Fresher' if is_fresher else 'Experienced Professional'

        prompts = {
            'summary': (
                f"Write a 3-4 sentence ATS-optimized professional summary for a resume.\n"
                f"Candidate type: {ctype}\n"
                f"Target role: {role}\n"
                f"Job description: {job_desc[:400]}\n"
                f"Existing resume context: {existing[:300]}\n\n"
                f"Rules:\n"
                f"- Start with degree/background + specialization\n"
                f"- Mention 2-3 specific skills from the job description\n"
                f"- End with what value you bring to the role\n"
                f"- Do NOT use cliches like 'Results-driven' or 'Dynamic'\n"
                f"- Under 75 words\n"
                f"- Return ONLY the summary text, no labels"
            ),
            'skills': (
                f"Improve and expand this resume's skills section for role: {role}.\n"
                f"Candidate: {ctype}\n"
                f"Job description keywords: {job_desc[:400]}\n"
                f"CURRENT resume content (extract existing skills from here): {existing[:600]}\n\n"
                f"Instructions:\n"
                f"1. Keep ALL skills already in the resume\n"
                f"2. ADD missing skills from the job description that the candidate likely has\n"
                f"3. Format in clear categories:\n"
                f"   Programming Languages: [exact list]\n"
                f"   Frameworks & Libraries: [exact list]\n"
                f"   Tools & Platforms: [exact list]\n"
                f"   Concepts & Techniques: [relevant to JD]\n\n"
                f"Return ONLY the formatted skills section, no explanation."
            ),
            'projects': (
                f"Write 2 strong resume project entries for a {ctype} targeting: {role}\n"
                f"Job description: {job_desc[:400]}\n"
                f"Existing context: {existing[:300]}\n\n"
                f"For EACH project use exactly this format:\n"
                f"[Descriptive Project Name] | [Tech Stack]\n"
                f"• [What you built + measurable outcome e.g. 92% accuracy on 5000 samples]\n"
                f"• [Key technical approach or algorithm used]\n"
                f"• [Technologies: Python, Scikit-learn, ...]\n"
                f"• GitHub: github.com/yourusername/project-slug\n\n"
                f"Make names and descriptions specific and realistic for ML/AI.\n"
                f"Return ONLY the two project entries."
            ),
            'certifications': (
                f"Suggest 3-4 specific, real certifications for someone targeting: {role}\n"
                f"Job description: {job_desc[:300]}\n\n"
                f"For each certification:\n"
                f"• [Exact Certification Name] | [Platform] | [~Duration or cost]\n"
                f"  Why relevant: [1 sentence]\n\n"
                f"Focus on: Google, Coursera/DeepLearning.AI, AWS, Microsoft, Kaggle.\n"
                f"Only suggest real, existing certifications.\n"
                f"Return ONLY the certification list."
            ),
        }
        return prompts.get(
            section_type,
            f"Write a professional {section_type} resume section for a {ctype} targeting {role}.\n"
            f"Job description context: {job_desc[:400]}\n"
            f"Return ONLY the section content, no labels or explanation."
        )

    def _get_template(self, section_type: str, ctx: dict) -> str:
        """Useful fallback templates when AI is unavailable."""
        role = ctx.get('target_role', '[Your Target Role]')
        mode = ctx.get('candidate_mode', 'Student')
        is_fresher = 'Fresher' in mode or 'Student' in mode or 'Internship' in mode

        if section_type == 'summary':
            if is_fresher:
                return (
                    f"B.Tech Computer Science student specializing in AI/ML at [Your University]. "
                    f"Experienced in building end-to-end machine learning pipelines using Python, "
                    f"Scikit-learn, and Pandas, with hands-on project work in classification and "
                    f"predictive modeling. Seeking a {role} role to apply ML skills to real-world problems."
                )
            return (
                f"Machine learning professional with [X] years of experience in [domain]. "
                f"Proven expertise in [skill1], [skill2], and [skill3]. "
                f"Track record of [achievement]. Seeking a {role} position to [goal]."
            )
        elif section_type == 'skills':
            return (
                "Programming Languages: Python, [add others from JD]\n"
                "Frameworks & Libraries: Scikit-learn, Pandas, NumPy, [add from JD]\n"
                "Tools & Platforms: Git, Jupyter Notebook, VS Code, Google Colab\n"
                "Concepts: Machine Learning, Data Preprocessing, [add from JD e.g. Classification, NLP]"
            )
        elif section_type == 'projects':
            return (
                f"[Your Project Name] | Python, Scikit-learn, Pandas, Streamlit\n"
                f"• Built an end-to-end ML pipeline for [problem] achieving [X]% accuracy on [N] samples\n"
                f"• Evaluated [N] models including [algorithm1] and [algorithm2], optimizing for [metric]\n"
                f"• Deployed as a Streamlit web application\n"
                f"• GitHub: github.com/yourusername/project-name\n\n"
                f"[Second Project Name] | Python, [Technologies]\n"
                f"• [Description with quantifiable result]\n"
                f"• [Key technical detail]\n"
                f"• GitHub: github.com/yourusername/project-name-2"
            )
        elif section_type == 'certifications':
            return (
                "• Machine Learning Specialization | Coursera (DeepLearning.AI) | 3 months\n"
                "• Python for Data Science and AI | IBM / Coursera | 5 weeks\n"
                "• [Add any completed certifications here]\n\n"
                "Tip: Complete at least one from DeepLearning.AI or Google to strengthen your ML profile."
            )
        return f"[Add your {section_type} content here - include specific details relevant to {role}]"

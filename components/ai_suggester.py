"""
AI Suggester Component
Generates improvement recommendations using Amazon Bedrock (primary),
Groq/Llama (secondary), or Google Gemini (tertiary).
"""

import time
import json
from dataclasses import dataclass, field
from typing import List, Optional

try:
    import boto3
    BEDROCK_AVAILABLE = True
except ImportError:
    BEDROCK_AVAILABLE = False

try:
    import google.generativeai as genai
    GEMINI_AVAILABLE = True
except ImportError:
    GEMINI_AVAILABLE = False

try:
    from groq import Groq as GroqClient
    GROQ_AVAILABLE = True
except ImportError:
    GROQ_AVAILABLE = False


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


def _build_smart_suggestions(ctx: dict) -> list:
    """Build resume-specific suggestions based on actual analysis data and candidate mode."""
    score            = ctx.get('score', 50)
    missing_keywords = ctx.get('missing_keywords', [])
    missing_sections = ctx.get('missing_sections', [])
    section_improv   = ctx.get('section_improvements', [])
    candidate_mode   = ctx.get('candidate_mode', '')

    is_fresher  = 'Student' in candidate_mode or 'Fresher' in candidate_mode
    is_intern   = 'Intern' in candidate_mode
    is_pro      = 'Professional' in candidate_mode
    is_student  = is_fresher or is_intern

    suggestions = []

    # 1. Missing keywords — always relevant, phrasing changes by mode
    if missing_keywords:
        top_kws = ', '.join(f'"{k}"' for k in missing_keywords[:5])
        if is_pro:
            tip = (f"Add these JD keywords to your Skills section: {top_kws}. "
                   f"Even experienced professionals lose ATS matches for missing exact keyword phrasing.")
        else:
            tip = (f"Add these high-priority keywords to your Skills or Projects section: {top_kws}. "
                   f"These appear in the JD but not in your resume.")
        suggestions.append(PrioritizedSuggestion(
            suggestion=tip, priority=1, category="keywords",
            impact_estimate="High", implementation_difficulty="Low"
        ))

    # 2. Missing sections — mode-aware
    if 'summary' in missing_sections:
        if is_pro:
            msg = "Add a 2-3 sentence executive summary highlighting your years of experience, key achievements, and specialization. Senior roles expect this."
        else:
            msg = "Add a 2-3 sentence Professional Summary tailored to this role — it's the first thing ATS systems read."
        suggestions.append(PrioritizedSuggestion(
            suggestion=msg, priority=1, category="structure",
            impact_estimate="High", implementation_difficulty="Low"
        ))

    if 'experience' in missing_sections:
        if is_pro:
            suggestions.append(PrioritizedSuggestion(
                suggestion="Your resume is missing a Work Experience section. This is critical for a Professional role — add your job history with achievements and metrics.",
                priority=1, category="structure", impact_estimate="High", implementation_difficulty="Medium"
            ))
        elif not is_student:
            suggestions.append(PrioritizedSuggestion(
                suggestion="Add a Work Experience section. Even internships, freelance, or part-time roles count significantly.",
                priority=1, category="structure", impact_estimate="High", implementation_difficulty="Medium"
            ))
        # For students/freshers — silently skip, missing experience is expected

    # 3. Score-based advice — mode-aware phrasing
    if score < 50:
        if is_pro:
            msg = (f"Your keyword match is low ({score}/100). "
                   f"Update your Skills section to mirror the JD's exact phrasing — "
                   f"ATS systems do literal keyword matching regardless of experience level.")
        else:
            msg = (f"Keyword match is low ({score}/100). "
                   f"Copy 3-4 exact phrases from the JD requirements directly into your Skills section.")
        suggestions.append(PrioritizedSuggestion(
            suggestion=msg, priority=1, category="keywords",
            impact_estimate="High", implementation_difficulty="Low"
        ))
    elif score < 70:
        if is_pro:
            msg = (f"Good match ({score}/100). "
                   f"Add the missing technical keywords to your Skills section — "
                   f"your experience is strong but ATS may filter on exact terms.")
        else:
            msg = (f"Good foundation ({score}/100). "
                   f"Adding the missing keywords to your project bullets is the fastest score boost.")
        suggestions.append(PrioritizedSuggestion(
            suggestion=msg, priority=2, category="keywords",
            impact_estimate="High", implementation_difficulty="Low"
        ))

    # 4. Mode-specific bullet/achievement advice
    if is_pro:
        suggestions.append(PrioritizedSuggestion(
            suggestion="Ensure every bullet quantifies business impact: revenue generated, team size led, % improvement, cost saved. Senior roles are evaluated on outcomes not just activities.",
            priority=2, category="experience", impact_estimate="High", implementation_difficulty="Low"
        ))
    elif is_intern:
        suggestions.append(PrioritizedSuggestion(
            suggestion="For internship applications: highlight coursework, personal projects, and any hackathon results. Format project metrics as 'Achieved X% accuracy using Y on Z dataset'.",
            priority=2, category="experience", impact_estimate="High", implementation_difficulty="Low"
        ))
    else:  # fresher/student
        suggestions.append(PrioritizedSuggestion(
            suggestion="Quantify every project metric you have. Format: 'Achieved X% accuracy on N samples using Y'. Numbers are what differentiate fresher resumes.",
            priority=2, category="experience", impact_estimate="High", implementation_difficulty="Low"
        ))

    # 5. Section-specific improvements from evaluator (deduplicated)
    if section_improv:
        unique = list(dict.fromkeys(section_improv))[:2]
        for imp in unique:
            suggestions.append(PrioritizedSuggestion(
                suggestion=imp, priority=3, category="content",
                impact_estimate="Medium", implementation_difficulty="Low"
            ))

    # 6. Strategy tip on keyword count
    if missing_keywords and len(missing_keywords) > 5:
        if is_pro:
            tip = (f"You have {len(missing_keywords)} missing keywords. "
                   f"Focus on the top 5 technical ones that directly match your actual experience — "
                   f"do not add skills you cannot defend in a senior interview.")
        else:
            tip = (f"You have {len(missing_keywords)} missing keywords. "
                   f"Focus on the top 5 technical ones. Adding skills you don't have will hurt in interviews.")
        suggestions.append(PrioritizedSuggestion(
            suggestion=tip, priority=3, category="strategy",
            impact_estimate="Medium", implementation_difficulty="Low"
        ))

    return suggestions[:7]


FALLBACK_SUGGESTIONS = _build_smart_suggestions({})  # empty fallback for import safety


class AISuggester:
    """Generates AI-powered resume improvement suggestions.
    Priority: Amazon Bedrock (Claude 3.5 Haiku) → Groq (Llama 3.3) → Google Gemini.
    """

    MAX_RETRIES = 3
    RETRY_DELAY = 2

    def __init__(self, api_key: Optional[str] = None, groq_key: Optional[str] = None,
                 aws_access_key: Optional[str] = None, aws_secret_key: Optional[str] = None,
                 aws_region: str = 'us-east-1'):
        self.model   = None   # Gemini
        self.groq    = None   # Groq
        self.bedrock = None   # Bedrock (primary)

        # PRIMARY: Bedrock
        if aws_access_key and aws_secret_key and BEDROCK_AVAILABLE:
            try:
                self.bedrock = boto3.client(
                    'bedrock-runtime',
                    region_name=aws_region,
                    aws_access_key_id=aws_access_key,
                    aws_secret_access_key=aws_secret_key,
                )
                print("[ATS] AI: Bedrock connected ✓")
            except Exception:
                self.bedrock = None

        # SECONDARY: Groq
        if groq_key and GROQ_AVAILABLE:
            try:
                self.groq = GroqClient(api_key=groq_key)
                print("[ATS] AI: Groq connected ✓")
            except Exception:
                self.groq = None

        # TERTIARY: Gemini
        if api_key and GEMINI_AVAILABLE:
            try:
                genai.configure(api_key=api_key)
                model_name = 'gemini-1.5-flash'
                try:
                    available = [m.name for m in genai.list_models()
                                 if 'generateContent' in m.supported_generation_methods]
                    preferred = [
                        'models/gemini-1.5-flash', 'models/gemini-1.5-flash-latest',
                        'models/gemini-1.5-flash-8b', 'models/gemini-2.0-flash-lite',
                        'models/gemini-2.0-flash', 'models/gemini-1.5-pro-latest',
                    ]
                    for pref in preferred:
                        if pref in available:
                            model_name = pref.replace('models/', '')
                            break
                except Exception:
                    pass
                self.model = genai.GenerativeModel(model_name)
                print("[ATS] AI: Gemini connected ✓")
            except Exception:
                self.model = None

    @property
    def has_ai(self) -> bool:
        return self.bedrock is not None or self.groq is not None or self.model is not None

    def _call_bedrock(self, prompt: str) -> str:
        """Call Amazon Bedrock — Claude 3.5 Haiku."""
        import json as _json
        response = self.bedrock.converse(
            modelId='us.anthropic.claude-haiku-4-5-20251001-v1:0',
            messages=[{'role': 'user', 'content': [{'text': prompt}]}],
            inferenceConfig={'maxTokens': 1024, 'temperature': 0.7}
        )
        return response['output']['message']['content'][0]['text'].strip()

    def _call_groq(self, prompt: str) -> str:
        """Call Groq — Llama 3.3 70B."""
        resp = self.groq.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=[{"role": "user", "content": prompt}],
            max_tokens=1024, temperature=0.7,
        )
        return resp.choices[0].message.content.strip()

    def _call_model(self, prompt: str, max_retries: int = 1) -> str:
        """Call AI: Bedrock → Groq → Gemini."""

        # PRIMARY: Bedrock
        if self.bedrock:
            try:
                return self._call_bedrock(prompt)
            except Exception as e:
                err = str(e)
                # Fall through on ANY Bedrock error — don't block the user
                print(f"[ATS] Bedrock unavailable ({err[:80]}), trying Groq...")
                # If it's a use-case/access issue, disable bedrock for this session
                if any(x in err for x in ['ResourceNotFoundException', 'AccessDenied',
                                           'use case', 'not submitted']):
                    self.bedrock = None  # stop retrying this session

        # SECONDARY: Groq
        if self.groq:
            try:
                return self._call_groq(prompt)
            except Exception as e:
                err = str(e)
                if '429' in err or 'rate' in err.lower():
                    print(f"[ATS] Groq rate limited, trying Gemini...")
                else:
                    raise Exception(f"Groq error: {err[:150]}")

        # TERTIARY: Gemini
        if self.model:
            for attempt in range(max_retries + 1):
                try:
                    resp = self.model.generate_content(prompt)
                    return resp.text.strip()
                except Exception as e:
                    err_str = str(e)
                    is_quota = '429' in err_str or 'quota' in err_str.lower()
                    if is_quota and attempt < max_retries:
                        time.sleep(8)
                        continue
                    raise

        raise Exception("No AI available. Add AWS credentials or GROQ_API_KEY to .env.")

    def generate_suggestions(self, analysis_context: dict) -> List[PrioritizedSuggestion]:
        """Generate improvement suggestions based on analysis results."""
        if not self.has_ai:
            return _build_smart_suggestions(analysis_context)

        prompt = self._build_prompt(analysis_context)

        for attempt in range(self.MAX_RETRIES):
            try:
                raw = self._call_model(prompt)
                suggestions = self._parse_suggestions(raw)
                if suggestions:
                    return suggestions
            except Exception as e:
                if attempt < self.MAX_RETRIES - 1:
                    time.sleep(self.RETRY_DELAY * (attempt + 1))
                continue

        return _build_smart_suggestions(analysis_context)

    def generate_content_for_section(self, section_type: str, context: dict) -> str:
        """Generate content for a missing resume section."""
        if not self.model:
            return self._get_template(section_type, context)

        prompt = self._build_content_prompt(section_type, context)

        for attempt in range(self.MAX_RETRIES):
            try:
                return self._call_model(prompt)
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
        job_desc = ctx.get('job_desc', '')[:1200]
        existing = ctx.get('existing_resume', '')[:2000]  # Use much more resume context
        role = ctx.get('target_role', 'the target role')
        mode = ctx.get('candidate_mode', 'Student / Fresher')
        is_fresher = 'Fresher' in mode or 'Student' in mode or 'Internship' in mode
        ctype = 'Student/Fresher' if is_fresher else 'Experienced Professional'

        prompts = {
            'summary': (
                f"Improve or write a professional summary for this {ctype} resume.\n\n"
                f"CURRENT RESUME CONTENT (use this as the basis):\n{existing[:1500]}\n\n"
                f"TARGET ROLE: {role}\n"
                f"JOB DESCRIPTION KEYWORDS: {job_desc[:500]}\n\n"
                f"Rules:\n"
                f"- Base the summary on the candidate's ACTUAL experience from their resume\n"
                f"- Reference their real projects, skills, and achievements\n"
                f"- Mention 2-3 specific skills from the job description\n"
                f"- Do NOT use cliches like 'Results-driven', 'Passionate', or 'Dynamic'\n"
                f"- Do NOT say '[Your University]' - use actual university name if visible in resume\n"
                f"- 3-4 sentences, under 80 words\n"
                f"- Return ONLY the summary text, nothing else"
            ),
            'skills': (
                f"You are an ATS resume expert. Improve this skills section for role: {role}.\n\n"
                f"CURRENT SKILLS (keep these, they are correct):\n{existing[:800]}\n\n"
                f"JOB DESCRIPTION TO MATCH:\n{job_desc[:800]}\n\n"
                f"YOUR TASK - do ALL of these:\n"
                f"1. Keep every existing skill category and item\n"
                f"2. Scan the JD and ADD missing technical skills the candidate realistically has given their projects\n"
                f"3. ADD skills that appear in the JD but not in the current skills list\n"
                f"4. If a JD skill is already present, do not add it again\n"
                f"5. Consider adding a new category if the JD emphasizes a domain not covered (e.g. 'Cloud Platforms', 'Databases')\n\n"
                f"IMPORTANT: The output MUST differ from the input - you must add at least 2-3 new items from the JD.\n"
                f"Return ONLY lines in format: Category: item1, item2, item3 (no bullets, no explanation)"
            ),
            'projects': (
                f"Improve the project bullets in this resume to better target: {role}\n\n"
                f"CURRENT RESUME PROJECTS (improve these, keep the actual project names and tech):\n{existing[:2000]}\n\n"
                f"JOB DESCRIPTION KEYWORDS TO INCORPORATE:\n{job_desc[:500]}\n\n"
                f"For each project, rewrite the bullets to:\n"
                f"1. Start with strong action verbs (Developed, Built, Achieved, Deployed)\n"
                f"2. Include specific metrics (accuracy %, dataset size, latency, etc.)\n"
                f"3. Incorporate relevant JD keywords naturally\n"
                f"4. Keep the real project names and actual tech stacks from the resume\n\n"
                f"Format: ProjectName | TechStack\n"
                f"- bullet 1\n"
                f"- bullet 2\n\n"
                f"Return ONLY the improved project entries."
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
        """Fallback templates that use actual JD content."""
        role = ctx.get('target_role', 'the target role') or 'ML Engineer'
        mode = ctx.get('candidate_mode', 'Student')
        is_fresher = 'Fresher' in mode or 'Student' in mode or 'Internship' in mode
        job_desc = ctx.get('job_desc', '')
        existing = ctx.get('existing_resume', '')
        # Normalize section type - proj_0, proj_1 → projects; exp_0, exp_1 → experience
        normalized = section_type
        if section_type.startswith('proj_'): normalized = 'projects'
        if section_type.startswith('exp_'):  normalized = 'experience'
        section_type = normalized

        # Extract real tech keywords from JD for use in templates
        jd_techs = []
        from components.keyword_analyzer import TECH_TERMS
        jd_lower = job_desc.lower()
        for term in sorted(TECH_TERMS, key=len, reverse=True):
            if term in jd_lower and len(term) > 3:
                jd_techs.append(term.title() if len(term.split()) == 1 else term)
            if len(jd_techs) >= 8:
                break
        jd_tech_str = ', '.join(jd_techs[:5]) if jd_techs else 'relevant technologies'

        # Extract existing skills from resume
        existing_skills = []
        for term in sorted(TECH_TERMS, key=len, reverse=True):
            if term in existing.lower() and len(term) > 3:
                existing_skills.append(term.title() if len(term.split()) == 1 else term)
            if len(existing_skills) >= 12:
                break

        if normalized == 'summary':
            # Extract actual university and degree from resume
            import re as _re
            uni_name = ''
            degree_area = 'AI/ML'
            for line in existing.split('\n'):
                l = line.strip()
                if any(kw in l.lower() for kw in ['university','institute','college','iit','nit','bits','jss','vit','srm','manipal']):
                    # Could be degree line or institution line
                    if len(l) < 60 and not _re.search(r'[@\d•-]', l):
                        uni_name = l
                if any(kw in l.lower() for kw in ['b.tech','bachelor','m.tech','master','b.sc']):
                    dm = _re.search(r'\(([^)]+)\)', l)
                    if dm:
                        degree_area = dm.group(1)

            uni_display = uni_name if uni_name else 'my university'
            # Get top 3 skills actually in the resume
            top_skills = ', '.join(existing_skills[:3]) if existing_skills else 'Python, Scikit-learn, and ML engineering'
            # Get top 3 relevant JD terms not already in summary context
            jd_terms = ', '.join(jd_techs[:3]) if jd_techs else 'machine learning'

            if is_fresher:
                # Build from actual resume content
                proj_count = existing.lower().count('- developed') + existing.lower().count('- built') + existing.lower().count('- engineered')
                award_line = ''
                if '1st' in existing.lower() or 'runner' in existing.lower() or 'winner' in existing.lower():
                    award_line = ' Award-winning hackathon participant.'
                return (
                    f"B.Tech {degree_area} student at {uni_display} with hands-on experience building "
                    f"production ML systems using {top_skills}."
                    f"{award_line} "
                    f"Seeking a {role} role to apply skills in {jd_terms}."
                )
            return (
                f"Machine learning professional with experience in {top_skills}. "
                f"Proven track record delivering production AI systems. "
                f"Seeking a {role} position to drive impact through {jd_terms}."
            )

        elif normalized == 'skills':
            import re as _re
            # Only match lines that look like skill categories (not email/phone/contact)
            CONTACT_SKIP = {'email', 'phone', 'linkedin', 'github', 'address', 'location', 'website'}
            skill_lines = []
            in_skills = False
            for line in existing.split('\n'):
                l = line.strip()
                # Detect entering/leaving skills section
                if _re.match(r'^SKILLS?\s*$', l, _re.I):
                    in_skills = True
                    continue
                if in_skills and _re.match(r'^(EDUCATION|EXPERIENCE|PROJECTS?|CERT|AWARD|SUMM|PROFILE|CONTACT)', l, _re.I) and len(l) < 30:
                    in_skills = False
                    continue

                m = _re.match(r'^([^:]{2,50}):\s*(.+)$', l)
                if m:
                    cat = m.group(1).strip()
                    items = m.group(2).strip()
                    # Skip contact fields
                    if cat.lower().split()[0] in CONTACT_SKIP:
                        continue
                    # Skip lines that look like sentences (contact info, coursework etc)
                    if any(w in cat.lower() for w in ['coursework', 'relevant', 'specializ', 'email', 'phone']):
                        continue
                    # Must be in skills section OR look like a skill category
                    if not in_skills:
                        cat_words = cat.lower().split()
                        is_skill_cat = any(w in cat_words for w in
                            ['programming','language','languages','ai','ml','data','science','libraries',
                             'tools','developer','frameworks','technical','skills','software','cloud'])
                        if not is_skill_cat:
                            continue

                    # Add JD terms to relevant categories
                    cat_lower = cat.lower()
                    if 'lang' in cat_lower:
                        for t in jd_techs:
                            if t.lower() in {'python','java','c++','r','scala','golang'} and t.lower() not in items.lower():
                                items += f', {t}'
                    elif any(w in cat_lower for w in ['lib','frame','tool']) and 'developer' not in cat_lower:
                        for t in jd_techs:
                            if t.lower() in {'tensorflow','pytorch','keras','numpy','pandas','scikit-learn','streamlit','fastapi','matplotlib','xgboost','lightgbm'} and t.lower() not in items.lower():
                                items += f', {t}'
                    skill_lines.append(f"{cat}: {items}")

            if skill_lines:
                return '\n'.join(skill_lines)
            # Fallback
            return (
                f"Programming Languages: Python, C, C++\n"
                f"Frameworks & Libraries: Scikit-learn, NumPy, Pandas, TensorFlow\n"
                f"Tools & Platforms: Git, Jupyter Notebook, VS Code, Google Colab\n"
                f"Concepts: Machine Learning, {jd_tech_str}"
            )

        elif normalized == 'projects':
            import re as _re
            # Extract projects section from resume
            proj_lines = []
            in_proj = False
            for line in existing.split('\n'):
                l = line.strip()
                if _re.match(r'^PROJECTS?\s*$', l, _re.I):
                    in_proj = True
                    continue
                if in_proj:
                    if _re.match(r'^(SKILLS?|EDUCATION|CERT|AWARD|SUMM|PROFILE|CONTACT|EXPERIENCE)', l, _re.I) and len(l) < 25:
                        break
                    if l:
                        proj_lines.append(l)
            if proj_lines:
                return '\n'.join(proj_lines[:20])
            return (
                f"[Project Name] | {', '.join(existing_skills[:3]) or 'Python, Scikit-learn'}\n"
                f"- Achieved [X]% accuracy on [N] samples using [algorithm]\n"
                f"- Deployed as [app/API] with [metric] performance"
            )

        elif normalized == 'certifications':
            relevant = []
            if any(t in jd_tech_str.lower() for t in ['machine learning','deep learning','tensorflow','pytorch']):
                relevant.append("Machine Learning Specialization | Coursera (DeepLearning.AI) | 3 months")
            if 'sql' in jd_lower:
                relevant.append("SQL for Data Science | Coursera / Mode Analytics | 2-4 weeks")
            if any(t in jd_lower for t in ['aws','sagemaker']):
                relevant.append("AWS Machine Learning Specialty | Amazon | 2-3 months")
            if any(t in jd_lower for t in ['tableau','powerbi','visualization']):
                relevant.append("Tableau Desktop Specialist | Tableau | 4-6 weeks")
            relevant.append("Python for Data Science and AI | IBM / Coursera | 5 weeks")
            return '\n'.join(f"- {c}" for c in relevant[:4])

        elif normalized in ('experience', 'contact'):
            return (
                f"[Job Title] | [Company Name] | [Start] – [End]\n"
                f"- Achieved [X]% improvement in [metric] using [technology/approach]\n"
                f"- Built/Designed [what] that [outcome with number]\n"
                f"- Collaborated with [team] to deliver [result] on time"
            )
        return (
            f"[Add your {section_type} content here for role: {role}]\n"
            f"Tip: Click 'AI Rewrite' above for AI-powered suggestions based on your resume."
        )
        return f"[Add your {section_type} content here - include specific details relevant to {role}]"

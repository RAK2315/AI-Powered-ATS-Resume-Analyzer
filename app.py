"""
AI-Powered ATS Resume Analyzer
Main Streamlit Application
"""

import streamlit as st
import os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from dotenv import load_dotenv
import pathlib
_base = pathlib.Path(__file__).parent
for _f in ['.env', '.env.example', '.env.local']:
    if (_base / _f).exists():
        load_dotenv(_base / _f)
        break

from components.pdf_parser import PDFParser
from components.score_calculator import ScoreCalculator
from components.keyword_analyzer import KeywordAnalyzer
from components.section_evaluator import SectionEvaluator
from components.ai_suggester import AISuggester

# ─────────────────────────────────────────────────────────
# PAGE CONFIG
# ─────────────────────────────────────────────────────────
st.set_page_config(
    page_title="ATS Resume Analyzer",
    page_icon="⚡",
    layout="wide",
    initial_sidebar_state="expanded"
)

GEMINI_KEY = os.getenv("GEMINI_API_KEY", "").strip().strip('"').strip("'")
# Reject placeholder values
_PLACEHOLDERS = ("", "your_key_here", "AIza...", "your-key-here", "your_api_key_here")
if GEMINI_KEY in _PLACEHOLDERS or len(GEMINI_KEY) < 20:
    GEMINI_KEY = ""
# Also try Streamlit secrets (for Streamlit Cloud deployment)
if not GEMINI_KEY:
    try:
        GEMINI_KEY = st.secrets.get("GEMINI_API_KEY", "").strip().strip('"').strip("'")
        if GEMINI_KEY in _PLACEHOLDERS or len(GEMINI_KEY) < 20:
            GEMINI_KEY = ""
    except Exception:
        pass

# ─────────────────────────────────────────────────────────
# GLOBAL CSS
# ─────────────────────────────────────────────────────────
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Space+Mono:wght@400;700&family=Syne:wght@400;600;700;800&display=swap');

html, body, [class*="css"] {
    font-family: 'Syne', sans-serif;
    background-color: #0a0a0f;
    color: #e8e8f0;
}
.stApp { background: linear-gradient(135deg,#0a0a0f 0%,#0f0f1a 50%,#0a0a0f 100%); }
#MainMenu, footer, header { visibility: hidden; }
.block-container { padding-top: 1.5rem; padding-bottom: 2rem; }

[data-testid="stSidebar"] {
    background: linear-gradient(180deg,#0d0d18 0%,#111120 100%);
    border-right: 1px solid #1e1e35;
}
[data-testid="stSidebar"] * { color: #c8c8e0 !important; }

/* NAV BUTTONS in sidebar */
.nav-btn {
    display: block;
    width: 100%;
    padding: 0.7rem 1rem;
    border-radius: 10px;
    border: 1px solid #2a2a4a;
    background: transparent;
    color: #9090c0 !important;
    font-family: 'Space Mono', monospace;
    font-size: 0.82rem;
    font-weight: 700;
    text-align: left;
    margin-bottom: 0.4rem;
    cursor: pointer;
    transition: all 0.2s;
}
.nav-btn.active {
    background: linear-gradient(135deg, rgba(123,47,255,0.25), rgba(68,68,204,0.2));
    border-color: #7b2fff;
    color: #c0a0ff !important;
}

.hero-title {
    font-size: 3rem; font-weight: 800;
    background: linear-gradient(135deg,#00d4ff,#7b2fff,#ff6b35);
    -webkit-background-clip: text; -webkit-text-fill-color: transparent;
    background-clip: text; letter-spacing: -0.02em; line-height: 1.1;
}
.hero-sub {
    font-size: 1rem; color: #7878a0;
    font-family: 'Space Mono', monospace; letter-spacing: 0.05em;
}
.hero-badge {
    display: inline-block;
    background: rgba(0,212,255,0.1); border: 1px solid rgba(0,212,255,0.3);
    color: #00d4ff; padding: 0.2rem 0.9rem; border-radius: 100px;
    font-size: 0.72rem; font-family: 'Space Mono', monospace;
    letter-spacing: 0.1em; margin-bottom: 1.2rem;
}
.neon-divider {
    height: 1px;
    background: linear-gradient(90deg,transparent,#7b2fff,#00d4ff,transparent);
    margin: 1.5rem 0; opacity: 0.4;
}
.score-card {
    background: linear-gradient(135deg,#111125,#1a1a30);
    border: 1px solid #2a2a4a; border-radius: 20px; padding: 2rem;
    text-align: center; position: relative; overflow: hidden;
}
.score-card::before {
    content: ''; position: absolute; top:0;left:0;right:0;bottom:0;
    background: radial-gradient(circle at 50% 0%,rgba(123,47,255,0.15) 0%,transparent 70%);
    pointer-events: none;
}
.score-number { font-size: 4.5rem; font-weight: 800; font-family: 'Space Mono', monospace; line-height: 1; }
.score-high { color: #00ff88; }
.score-mid  { color: #ffb800; }
.score-low  { color: #ff4444; }
.score-label { color: #a0a0c8; font-size: 0.95rem; font-weight: 600; margin-top: 0.4rem; }

.metric-card {
    background: #111125; border: 1px solid #1e1e35; border-radius: 12px;
    padding: 1rem; text-align: center;
}
.metric-value { font-size: 1.7rem; font-weight: 700; font-family: 'Space Mono', monospace; color: #00d4ff; }
.metric-label { font-size: 0.8rem; color: #8888b0; font-weight: 600; margin-top: 0.3rem; }

.keyword-container { display: flex; flex-wrap: wrap; gap: 0.5rem; margin: 0.5rem 0; }
.keyword-pill {
    padding: 0.3rem 0.8rem; border-radius: 100px;
    font-size: 0.78rem; font-family: 'Space Mono', monospace; font-weight: 700;
}
.pill-technical  { background: rgba(123,47,255,0.2);  border: 1px solid rgba(123,47,255,0.5);  color: #b060ff; }
.pill-soft_skill { background: rgba(0,212,255,0.15);  border: 1px solid rgba(0,212,255,0.4);   color: #00d4ff; }
.pill-industry_specific { background: rgba(255,107,53,0.15); border: 1px solid rgba(255,107,53,0.4); color: #ff6b35; }
.pill-general    { background: rgba(255,184,0,0.15);  border: 1px solid rgba(255,184,0,0.4);   color: #ffb800; }

.section-bar-wrapper { margin: 0.8rem 0; }
.section-bar-bg { background: #1a1a2e; border-radius: 100px; height: 8px; overflow: hidden; }
.section-bar-fill { height: 100%; border-radius: 100px; }

.suggestion-card {
    background: linear-gradient(135deg,#111125,#141430);
    border: 1px solid #1e1e40; border-left: 3px solid #7b2fff;
    border-radius: 12px; padding: 1.2rem 1.5rem; margin: 0.7rem 0;
}
.suggestion-priority {
    display: inline-block; background: #7b2fff; color: white;
    font-size: 0.65rem; font-family: 'Space Mono', monospace;
    padding: 0.15rem 0.5rem; border-radius: 4px;
    letter-spacing: 0.1em; margin-bottom: 0.5rem;
}
.suggestion-text { font-size: 0.92rem; line-height: 1.5; color: #d0d0e8; }
.tag-row { margin-top: 0.6rem; display: flex; gap: 0.5rem; flex-wrap: wrap; }
.tag {
    font-size: 0.7rem; font-family: 'Space Mono', monospace;
    padding: 0.15rem 0.5rem; border-radius: 4px;
    background: rgba(255,255,255,0.05); color: #8888a8;
    border: 1px solid rgba(255,255,255,0.1);
}

/* Fix this section card */
.fix-card {
    background: linear-gradient(135deg,#0d1a2a,#101828);
    border: 1px solid #1a3050; border-left: 3px solid #00d4ff;
    border-radius: 10px; padding: 1rem 1.2rem; margin: 0.5rem 0;
    font-family: 'Space Mono', monospace; font-size: 0.82rem;
    line-height: 1.7; color: #a0c8e0; white-space: pre-wrap;
}
.generated-content {
    background: #0d1a2a; border: 1px solid #1a3050; border-left: 3px solid #00d4ff;
    border-radius: 10px; padding: 1.2rem; font-family: 'Space Mono', monospace;
    font-size: 0.85rem; line-height: 1.7; color: #a0c8e0; white-space: pre-wrap;
}
.missing-section-card {
    background: rgba(255,68,68,0.07); border: 1px solid rgba(255,68,68,0.25);
    border-radius: 10px; padding: 0.8rem 1rem; margin: 0.4rem 0;
}
.section-header {
    font-size: 1rem; font-weight: 700; color: #c8c8ff;
    letter-spacing: 0.05em; text-transform: uppercase;
    margin: 1.2rem 0 0.6rem;
}

/* Tabs */
.stTabs [data-baseweb="tab-list"] {
    background: #111125; border-radius: 12px;
    border: 1px solid #2a2a4a; padding: 0.4rem; gap: 0.4rem;
}
.stTabs [data-baseweb="tab"] {
    background: transparent !important; color: #9090b8 !important;
    border-radius: 8px !important; font-family: 'Space Mono', monospace !important;
    font-size: 0.78rem !important; font-weight: 600 !important;
    border: 1px solid transparent !important; padding: 0.5rem 0.8rem !important;
    transition: all 0.2s ease !important;
}
.stTabs [data-baseweb="tab"]:hover {
    background: rgba(123,47,255,0.1) !important;
    border-color: rgba(123,47,255,0.3) !important; color: #c0c0e8 !important;
}
.stTabs [aria-selected="true"] {
    background: linear-gradient(135deg,#7b2fff,#4444cc) !important;
    color: white !important; border-color: transparent !important;
    box-shadow: 0 4px 15px rgba(123,47,255,0.4) !important;
}

/* Buttons */
.stButton > button {
    background: linear-gradient(135deg,#7b2fff,#4444cc) !important;
    color: white !important; border: none !important;
    border-radius: 10px !important; font-family: 'Space Mono', monospace !important;
    font-weight: 700 !important; letter-spacing: 0.05em !important;
    padding: 0.6rem 1.5rem !important; width: 100% !important;
    transition: all 0.3s ease !important;
}
.stButton > button:hover {
    transform: translateY(-2px) !important;
    box-shadow: 0 8px 25px rgba(123,47,255,0.4) !important;
}
/* Secondary button style (outline) */
.stButton > button[kind="secondary"] {
    background: transparent !important;
    border: 1px solid #2a2a4a !important; color: #9090b8 !important;
}

[data-testid="stFileUploader"] {
    background: #111125 !important; border: 2px dashed #2a2a4a !important;
    border-radius: 16px !important;
}
.stTextArea textarea, .stTextInput input {
    background: #111125 !important; border: 1px solid #2a2a4a !important;
    border-radius: 10px !important; color: #e0e0f0 !important;
    font-family: 'Space Mono', monospace !important;
}
.stInfo    { background: rgba(0,212,255,0.08)  !important; border: 1px solid rgba(0,212,255,0.2)  !important; border-radius: 10px !important; }
.stWarning { background: rgba(255,184,0,0.08)  !important; border: 1px solid rgba(255,184,0,0.2)  !important; border-radius: 10px !important; }
.stError   { background: rgba(255,68,68,0.08)  !important; border: 1px solid rgba(255,68,68,0.2)  !important; border-radius: 10px !important; }
.stSuccess { background: rgba(0,255,136,0.08)  !important; border: 1px solid rgba(0,255,136,0.2)  !important; border-radius: 10px !important; }
.streamlit-expanderHeader {
    background: #111125 !important; border: 1px solid #1e1e35 !important;
    border-radius: 10px !important; color: #c0c0e0 !important;
}
.stProgress > div > div > div > div {
    background: linear-gradient(90deg,#7b2fff,#00d4ff) !important;
}
</style>
""", unsafe_allow_html=True)

# ─────────────────────────────────────────────────────────
# SESSION STATE
# ─────────────────────────────────────────────────────────
defaults = {
    'page': 'analyzer',
    'analysis_done': False,
    'results': None,
    'generated_sections': {},
    'fixed_sections': {},
    'candidate_mode': '🎓 Student / Fresher',
}
for k, v in defaults.items():
    if k not in st.session_state:
        st.session_state[k] = v

# ─────────────────────────────────────────────────────────
# SIDEBAR
# ─────────────────────────────────────────────────────────
with st.sidebar:
    st.markdown("""
    <div style='padding:0.5rem 0 1rem'>
        <div style='font-size:1.1rem;font-weight:800;color:#c0c0ff;letter-spacing:-0.01em'>⚡ ATS Analyzer</div>
        <div style='font-size:0.7rem;color:#3a3a6a;font-family:Space Mono,monospace'>AI for Bharat Hackathon 2025</div>
    </div>
    """, unsafe_allow_html=True)

    st.markdown("**Navigate**")

    pages = [
        ("🔍 Resume Analyzer", "analyzer"),
        ("📄 Resume Builder", "builder"),
    ]
    for label, page_key in pages:
        is_active = st.session_state.page == page_key
        if st.button(label, key=f"nav_{page_key}",
                     use_container_width=True,
                     type="primary" if is_active else "secondary"):
            st.session_state.page = page_key
            st.rerun()

    st.markdown("---")
    st.markdown("**⚙️ Candidate Mode**")
    mode = st.radio(
        "Mode", ["🎓 Student / Fresher", "💼 Internship Applicant", "👨‍💼 Experienced Professional"],
        index=["🎓 Student / Fresher","💼 Internship Applicant","👨‍💼 Experienced Professional"].index(
            st.session_state.candidate_mode),
        label_visibility="collapsed"
    )
    st.session_state.candidate_mode = mode

    if not GEMINI_KEY:
        st.markdown("---")
        st.markdown("""
        <div style='background:rgba(255,184,0,0.08);border:1px solid rgba(255,184,0,0.2);
                    border-radius:8px;padding:0.8rem;font-size:0.78rem;color:#c8a000'>
            ⚠️ <b>Gemini AI not connected.</b><br><br>
            <b>Locally:</b> Open <code>.env</code> and set:<br>
            <code>GEMINI_API_KEY=AIzaSy...</code><br><br>
            <b>Streamlit Cloud:</b> App Settings → Secrets → add:<br>
            <code>GEMINI_API_KEY = "AIzaSy..."</code><br><br>
            <a href='https://aistudio.google.com' target='_blank' style='color:#c8a000'>
            Get free key at aistudio.google.com →</a>
        </div>
        """, unsafe_allow_html=True)

    st.markdown("---")
    st.markdown("""
    <div style='font-size:0.75rem;color:#3a3a5a;line-height:1.7'>
        <b style='color:#5a5a8a'>Score Guide</b><br>
        🟢 80–100 Excellent<br>
        🟡 60–79 Good<br>
        🟠 40–59 Moderate<br>
        🔴 0–39 Low match
    </div>
    """, unsafe_allow_html=True)


# ─────────────────────────────────────────────────────────
# PAGE ROUTER
# ─────────────────────────────────────────────────────────
if st.session_state.page == 'builder':
    from pages.cv_builder import render_cv_builder
    render_cv_builder(gemini_key=GEMINI_KEY)
    st.stop()


# ─────────────────────────────────────────────────────────
# ANALYZER PAGE
# ─────────────────────────────────────────────────────────
st.markdown("""
<div style='text-align:center;padding:2rem 0 1.5rem'>
    <div class='hero-badge'>⚡ AI FOR BHARAT HACKATHON 2025</div>
    <div class='hero-title'>ATS Resume Analyzer</div>
    <div class='hero-sub' style='margin-top:0.4rem'>Beat the bots. Land the interview.</div>
</div>
""", unsafe_allow_html=True)

st.markdown('<div class="neon-divider"></div>', unsafe_allow_html=True)

col_left, col_right = st.columns([1, 1], gap="large")
with col_left:
    st.markdown('<div class="section-header">📄 Your Resume</div>', unsafe_allow_html=True)
    uploaded_file = st.file_uploader("Upload Resume PDF", type=['pdf'],
                                     label_visibility="collapsed")
    if uploaded_file:
        st.success(f"✓ {uploaded_file.name} ({uploaded_file.size // 1024} KB)")

with col_right:
    st.markdown('<div class="section-header">💼 Job Description</div>', unsafe_allow_html=True)
    job_desc = st.text_area(
        "Paste job description", height=200, label_visibility="collapsed",
        placeholder="Paste the full job description here...\n\nInclude responsibilities, requirements, skills needed etc."
    )
    if job_desc:
        st.caption(f"📝 {len(job_desc.split())} words")

st.markdown('<div class="neon-divider"></div>', unsafe_allow_html=True)

_, col_btn, _ = st.columns([1, 1, 1])
with col_btn:
    analyze_clicked = st.button("⚡ ANALYZE RESUME", use_container_width=True)


# ─────────────────────────────────────────────────────────
# ANALYSIS ENGINE
# ─────────────────────────────────────────────────────────
if analyze_clicked:
    if not uploaded_file:
        st.error("⚠️ Please upload your resume PDF first.")
    elif not job_desc or len(job_desc.strip()) < 50:
        st.error("⚠️ Please paste a job description (at least 50 characters).")
    else:
        with st.spinner(""):
            progress = st.progress(0)
            status = st.empty()
            try:
                status.markdown("**⚙️ Extracting text from PDF...**")
                progress.progress(10)
                parser = PDFParser()
                validation = parser.validate_pdf(uploaded_file)
                if not validation.is_valid:
                    st.error(f"❌ PDF Error: {'; '.join(validation.errors)}")
                    st.stop()

                extraction = parser.extract_text(uploaded_file)
                if not extraction.success:
                    st.error(f"❌ Could not extract text: {'; '.join(extraction.errors)}")
                    st.stop()

                resume_text = extraction.text
                progress.progress(25)

                status.markdown("**📊 Calculating ATS score...**")
                score_calc = ScoreCalculator()
                metrics = score_calc.get_detailed_metrics(resume_text, job_desc)
                progress.progress(45)

                status.markdown("**🔍 Analyzing keyword gaps...**")
                kw_analyzer = KeywordAnalyzer()
                job_keywords = kw_analyzer.extract_keywords(job_desc)
                missing_kws = kw_analyzer.find_missing_keywords(resume_text, job_keywords)
                ranked_kws = kw_analyzer.rank_by_importance(missing_kws)
                progress.progress(62)

                status.markdown("**📋 Evaluating sections...**")
                evaluator = SectionEvaluator()
                evaluator.set_full_resume_text(resume_text)
                sections = evaluator.identify_sections(resume_text)
                completeness = evaluator.evaluate_completeness(sections)
                section_scores = {}
                for name, section in sections.items():
                    section_scores[name] = evaluator.score_section(section, job_desc)

                # Don't penalize freshers for missing work experience
                mode = st.session_state.candidate_mode
                if mode in ["🎓 Student / Fresher", "💼 Internship Applicant"]:
                    completeness.missing_sections = [
                        s for s in completeness.missing_sections if s != 'experience'
                    ]
                progress.progress(80)

                status.markdown("**🤖 Generating AI suggestions...**")
                all_improvements = []
                for sc in section_scores.values():
                    all_improvements.extend(sc.improvement_areas)

                suggester = AISuggester(api_key=GEMINI_KEY or None)

                # ── Ask Gemini for holistic ATS score (more accurate than TF-IDF alone) ──
                ai_score = None
                if suggester.model:
                    try:
                        score_prompt = (
                            f"You are an ATS (Applicant Tracking System) expert.\n\n"
                            f"Rate how well this resume matches the job description on a scale of 0-100.\n\n"
                            f"RESUME:\n{resume_text[:2000]}\n\n"
                            f"JOB DESCRIPTION:\n{job_desc[:1200]}\n\n"
                            f"Candidate type: {mode}\n\n"
                            f"Scoring criteria (be fair and realistic):\n"
                            f"- 70-85: Good match, has most required skills, solid projects\n"
                            f"- 50-69: Decent match, some gaps but promising\n"
                            f"- 30-49: Partial match, missing several key requirements\n"
                            f"- 0-29: Poor match, major gaps\n\n"
                            f"For students/freshers: judge based on projects, skills, and potential — "
                            f"NOT on missing work experience.\n\n"
                            f"Return ONLY a JSON object: {{\"score\": <number>, \"reasoning\": \"<1 sentence>\"}}"
                        )
                        raw_score_resp = suggester._call_model(score_prompt)
                        import json, re as _re
                        raw = raw_score_resp
                        # Strip markdown code fences
                        raw = _re.sub(r'^```(?:json)?\s*', '', raw)
                        raw = _re.sub(r'\s*```\s*$', '', raw).strip()
                        # Try to find JSON object in response
                        json_match = _re.search(r'\{[^}]+\}', raw, _re.DOTALL)
                        if json_match:
                            raw = json_match.group(0)
                        parsed_score = json.loads(raw)
                        ai_score = max(0, min(100, int(float(str(parsed_score['score'])))))
                        ai_reasoning = str(parsed_score.get('reasoning', ''))[:200]
                        # Blend: 60% AI + 40% TF-IDF for stability
                        blended = int(0.6 * ai_score + 0.4 * metrics.normalized_score)
                        from components.score_calculator import ScoreMetrics
                        metrics = ScoreMetrics(
                            raw_similarity=metrics.raw_similarity,
                            normalized_score=blended,
                            technical_match=metrics.technical_match,
                            keyword_density=metrics.keyword_density,
                            length_ratio=metrics.length_ratio,
                        )
                    except Exception:
                        ai_score = None
                        ai_reasoning = ''

                suggestions = suggester.generate_suggestions({
                    'score': metrics.normalized_score,
                    'missing_keywords': [k.term for k in ranked_kws[:10]],
                    'missing_sections': completeness.missing_sections,
                    'job_desc': job_desc,
                    'section_improvements': all_improvements,
                    'candidate_mode': mode,
                })
                progress.progress(100)
                status.empty(); progress.empty()

                st.session_state.results = {
                    'resume_text': resume_text, 'job_desc': job_desc,
                    'metrics': metrics, 'ranked_keywords': ranked_kws,
                    'section_scores': section_scores, 'completeness': completeness,
                    'suggestions': suggestions, 'suggester': suggester,
                    'ai_score': ai_score, 'ai_reasoning': ai_reasoning if ai_score else '',
                }
                st.session_state.analysis_done = True
                st.session_state.fixed_sections = {}
                st.session_state.generated_sections = {}

            except Exception as e:
                status.empty(); progress.empty()
                st.error(f"❌ Analysis failed: {str(e)}")


# ─────────────────────────────────────────────────────────
# RESULTS
# ─────────────────────────────────────────────────────────
if st.session_state.analysis_done and st.session_state.results:
    r = st.session_state.results
    metrics = r['metrics']
    score = metrics.normalized_score
    mode = st.session_state.candidate_mode
    ai_score = r.get('ai_score')
    ai_reasoning = r.get('ai_reasoning', '')

    st.markdown('<div class="neon-divider"></div>', unsafe_allow_html=True)

    # ── Results header row ─────────────────────────────────────────────────
    h1, h2 = st.columns([3, 1])
    with h1:
        st.markdown(
            f"## 📊 Results &nbsp;"
            f"<span style='font-size:0.8rem;background:rgba(123,47,255,0.2);"
            f"border:1px solid rgba(123,47,255,0.4);color:#b060ff;"
            f"padding:0.2rem 0.8rem;border-radius:100px;font-family:Space Mono'>"
            f"{mode}</span>",
            unsafe_allow_html=True)
    with h2:
        if st.button("🚀 Implement All in CV Builder", use_container_width=True,
                     key="implement_all_btn",
                     help="Jump to CV Builder — auto-fills from your resume with AI improvements"):
            st.session_state.cv_prefilled = False  # force re-parse prompt
            st.session_state.page = "builder"
            st.rerun()

    # ── Score card row ─────────────────────────────────────────────────────
    col_score, col_metrics = st.columns([1, 2], gap="large")

    with col_score:
        sc_cls = "score-high" if score >= 70 else "score-mid" if score >= 45 else "score-low"
        emoji  = "🟢" if score >= 70 else "🟡" if score >= 45 else "🔴"
        ctx = ("Strong match! Minor tweaks will make it excellent." if score >= 70
               else "Good foundation — add missing keywords to improve." if score >= 45
               else "Needs work — see suggestions below to boost score.")
        score_method = f"<div style='font-size:0.68rem;color:#5a5a7a;margin-top:0.3rem'>{'🤖 AI-enhanced score' if ai_score else '📐 TF-IDF score'}</div>"
        ai_note = f"<div style='font-size:0.75rem;color:#9090c8;margin-top:0.5rem;font-style:italic'>\"{ai_reasoning}\"</div>" if ai_reasoning else ""
        st.markdown(f"""
        <div class="score-card">
          <div style='font-size:0.7rem;color:#9090c0;letter-spacing:0.18em;
                      text-transform:uppercase;margin-bottom:0.3rem'>ATS SCORE</div>
          <div class="score-number {sc_cls}" style='font-size:3.2rem'>{score}</div>
          <div class="score-label" style='font-size:1rem'>{emoji} Out of 100</div>
          <div style='margin-top:0.5rem;font-size:0.82rem;color:#b0b0d8;font-weight:600'>{ctx}</div>
          {score_method}{ai_note}
        </div>""", unsafe_allow_html=True)

    with col_metrics:
        tech_pct = int(metrics.technical_match * 100)
        kw_pct   = int(metrics.keyword_density * 100)
        miss_cnt = len(r['ranked_keywords'])
        sec_cnt  = len(r['section_scores'])

        # Bigger, brighter metric cards
        def _mcol(val, label, color="#00d4ff"):
            return f"""<div style='background:rgba(255,255,255,0.06);border:1px solid rgba(255,255,255,0.12);
                        border-radius:10px;padding:0.9rem 0.6rem;text-align:center;flex:1;min-width:90px'>
                        <div style='font-size:1.6rem;font-weight:800;color:{color};
                                    font-family:Space Mono,monospace'>{val}</div>
                        <div style='font-size:0.75rem;color:#a0a0c0;margin-top:3px;
                                    text-transform:uppercase;letter-spacing:0.05em'>{label}</div>
                       </div>"""

        tech_color = "#00d4ff" if tech_pct >= 50 else "#ffbb33" if tech_pct >= 25 else "#ff5566"
        kw_color   = "#00d4ff" if kw_pct   >= 40 else "#ffbb33" if kw_pct   >= 20 else "#ff5566"
        miss_color = "#ff5566" if miss_cnt  > 10 else "#ffbb33" if miss_cnt  > 5  else "#00cc66"

        st.markdown(f"""<div style='display:flex;gap:0.7rem;flex-wrap:wrap;margin-bottom:0.8rem'>
            {_mcol(f"{tech_pct}%", "Tech Match",    tech_color)}
            {_mcol(f"{kw_pct}%",  "KW Density",    kw_color)}
            {_mcol(miss_cnt,      "Missing KWs",   miss_color)}
            {_mcol(sec_cnt,       "Sections Found","#b060ff")}
        </div>""", unsafe_allow_html=True)

        # Missing sections — more visible
        for ms in r['completeness'].missing_sections:
            st.markdown(f"""
            <div style='background:rgba(255,68,68,0.1);border:1px solid rgba(255,68,68,0.3);
                        border-radius:8px;padding:0.4rem 0.8rem;margin-bottom:0.4rem;font-size:0.85rem'>
                ⚠️ Missing <b style='color:#ff8888'>{ms.title()}</b> section — add it to boost your score
            </div>""", unsafe_allow_html=True)

    # ── TABS ──────────────────────────────────────────────────────────────
    st.markdown("<br>", unsafe_allow_html=True)
    tab_kw, tab_sec, tab_sugg, tab_gen = st.tabs([
        "🔍 Missing Keywords", "📋 Section Analysis",
        "🤖 AI Suggestions", "✨ Generate Content"
    ])

    # ── TAB 1: KEYWORDS ────────────────────────────────────────────────────
    with tab_kw:
        ranked = r['ranked_keywords']
        if not ranked:
            st.success("🎉 No major keyword gaps found! Your resume covers the JD well.")
        else:
            # Summary bar
            tech_kws  = [k for k in ranked if k.category == 'technical']
            soft_kws  = [k for k in ranked if k.category == 'soft_skill']
            other_kws = [k for k in ranked if k.category not in ('technical','soft_skill')]

            st.markdown(f"""
            <div style='background:rgba(255,100,100,0.08);border:1px solid rgba(255,100,100,0.2);
                        border-radius:10px;padding:0.8rem 1.1rem;margin-bottom:1rem'>
              <span style='font-size:1.1rem;font-weight:800;color:#ff8888'>{len(ranked)}</span>
              <span style='color:#c0c0d8;font-size:0.9rem'> keywords from the JD are missing from your resume.</span>
              <br><span style='color:#888;font-size:0.8rem'>
                🔧 {len(tech_kws)} technical &nbsp;·&nbsp;
                💡 {len(soft_kws)} soft skills &nbsp;·&nbsp;
                📌 {len(other_kws)} other
              </span>
            </div>""", unsafe_allow_html=True)

            # Color map per category
            cat_styles = {
                'technical':         ('#00d4ff', '#0a1a2a', '🔧'),
                'soft_skill':        ('#b060ff', '#180a2a', '💡'),
                'industry_specific': ('#ff9900', '#2a1a00', '🏭'),
                'general':           ('#60c060', '#0a200a', '📌'),
            }

            cats = {}
            for kw in ranked:
                cats.setdefault(kw.category, []).append(kw)

            cat_labels = {
                'technical': '🔧 Technical Skills',
                'soft_skill': '💡 Soft Skills',
                'industry_specific': '🏭 Industry Specific',
                'general': '📌 General Terms',
            }

            for cat, kws in cats.items():
                color, bg, icon = cat_styles.get(cat, ('#aaaaff', '#111130', '•'))
                label = cat_labels.get(cat, cat.title())
                st.markdown(f"<div style='font-size:0.85rem;font-weight:700;color:{color};"
                            f"margin:1rem 0 0.5rem'>{label}</div>", unsafe_allow_html=True)

                # Card grid — 2 columns
                cols = st.columns(2)
                for i, kw in enumerate(kws[:20]):
                    with cols[i % 2]:
                        # Importance bar width
                        imp = max(10, 100 - (kw.rank - 1) * 8)
                        st.markdown(f"""
                        <div style='background:{bg};border:1px solid {color}33;border-left:3px solid {color};
                                    border-radius:8px;padding:0.6rem 0.8rem;margin-bottom:0.5rem'>
                          <div style='display:flex;justify-content:space-between;align-items:center'>
                            <span style='font-weight:700;color:{color};font-size:0.88rem'>
                              {icon} {kw.term}
                            </span>
                            <span style='font-size:0.65rem;color:#666;background:rgba(255,255,255,0.05);
                                         padding:1px 5px;border-radius:4px'>#{kw.rank}</span>
                          </div>
                          <div style='background:rgba(255,255,255,0.05);border-radius:3px;
                                      height:3px;margin:5px 0'>
                            <div style='background:{color};width:{imp}%;height:3px;border-radius:3px'></div>
                          </div>
                          <div style='font-size:0.72rem;color:#888;margin-top:3px'>
                            {kw.suggestions[0] if kw.suggestions else 'Add to Skills or Projects section'}
                          </div>
                        </div>""", unsafe_allow_html=True)

            # Quick-add to CV builder
            st.markdown("---")
            st.markdown("**⚡ Quick action:**")
            c1, c2 = st.columns(2)
            with c1:
                top_tech = [k.term for k in tech_kws[:5]]
                if top_tech and st.button(f"➕ Add top keywords to CV Builder", use_container_width=True):
                    # Store top missing keywords for CV builder to pick up
                    st.session_state['pending_keywords'] = top_tech
                    st.session_state.page = "builder"
                    st.session_state.cv_prefilled = False
                    st.rerun()
            with c2:
                if st.button("🚀 Go to CV Builder", use_container_width=True):
                    st.session_state.page = "builder"
                    st.rerun()

    # ── TAB 2: SECTION ANALYSIS ────────────────────────────────────────────
    with tab_sec:
        section_scores = r['section_scores']
        completeness   = r['completeness']

        if not section_scores:
            st.warning("⚠️ Could not identify standard resume sections.")
        else:
            st.markdown(f"**Structure Score: {completeness.total_score}/100** — {completeness.overall_feedback}")
            st.markdown("<br>", unsafe_allow_html=True)

            for name, sc in section_scores.items():
                bar_color = '#00ff88' if sc.score >= 75 else '#ffb800' if sc.score >= 50 else '#ff4444'
                icon = '✅' if sc.score >= 60 else '⚠️'

                st.markdown(f"""
                <div class="section-bar-wrapper">
                    <div style='display:flex;justify-content:space-between;margin-bottom:0.3rem;font-size:0.88rem'>
                        <span>{icon} <b>{sc.section_name}</b></span>
                        <span style='font-family:Space Mono;color:{bar_color};font-weight:700'>{sc.score}/100</span>
                    </div>
                    <div class="section-bar-bg">
                        <div class="section-bar-fill" style='width:{sc.score}%;background:{bar_color}'></div>
                    </div>
                </div>""", unsafe_allow_html=True)

                if sc.improvement_areas:
                    with st.expander(f"💡 Improve {sc.section_name}  ({sc.score}/100)"):
                        for area in sc.improvement_areas:
                            st.markdown(f"→ {area}")

                        # ── FIX THIS SECTION button ──────────────────────
                        fix_key = f"fix_{name}"
                        fix_result_key = f"fixed_{name}"

                        if st.button(f"✨ Fix This Section with AI",
                                     key=fix_key, use_container_width=True):
                            if not GEMINI_KEY:
                                st.warning("Add GEMINI_API_KEY to your .env file for AI-powered fixes.")
                            else:
                                with st.spinner(f"Rewriting {sc.section_name}..."):
                                    suggester = r['suggester']
                                    # Extract clean role name from JD (first non-empty short line)
                                    jd_lines = [l.strip() for l in r['job_desc'].split('\n') if l.strip()]
                                    clean_role = next((l for l in jd_lines if len(l) < 60 and not l.startswith(('#','*','-'))), jd_lines[0] if jd_lines else 'ML Engineer')
                                    improved = suggester.generate_content_for_section(
                                        name,
                                        {
                                            'job_desc': r['job_desc'],
                                            'existing_resume': r['resume_text'],
                                            'section_content': sc.content if hasattr(sc, 'content') else '',
                                            'target_role': clean_role,
                                            'candidate_mode': st.session_state.candidate_mode,
                                            'issues': '\n'.join(sc.improvement_areas),
                                        }
                                    )
                                    st.session_state.fixed_sections[fix_result_key] = improved

                        if fix_result_key in st.session_state.fixed_sections:
                            st.markdown(f"**✅ Improved {sc.section_name}:**")
                            st.markdown(
                                f'<div class="fix-card">{st.session_state.fixed_sections[fix_result_key]}</div>',
                                unsafe_allow_html=True
                            )
                            st.download_button(
                                f"⬇️ Download",
                                data=st.session_state.fixed_sections[fix_result_key],
                                file_name=f"improved_{name}.txt",
                                mime="text/plain",
                                key=f"dl_fix_{name}"
                            )

            if completeness.missing_sections:
                st.markdown("---")
                st.markdown("### ❌ Missing Sections")
                for ms in completeness.missing_sections:
                    st.markdown(f"""
                    <div class="missing-section-card">
                        ⚠️ &nbsp;<b>{ms.title()}</b> section not found —
                        add it to significantly improve your ATS score.
                    </div>""", unsafe_allow_html=True)

    # ── TAB 3: AI SUGGESTIONS ──────────────────────────────────────────────
    with tab_sugg:
        suggestions = r['suggestions']
        if not GEMINI_KEY:
            st.info("💡 Add GEMINI_API_KEY to .env for personalized AI suggestions. Showing general recommendations.")

        priority_labels = {
            1: "🔴 CRITICAL", 2: "🟠 HIGH",
            3: "🟡 MEDIUM",  4: "🟢 LOW", 5: "🔵 OPTIONAL"
        }
        for s in suggestions:
            p_label = priority_labels.get(s.priority, f"#{s.priority}")
            st.markdown(f"""
            <div class="suggestion-card">
                <div class="suggestion-priority">{p_label} PRIORITY</div>
                <div class="suggestion-text">{s.suggestion}</div>
                <div class="tag-row">
                    <span class="tag">📂 {s.category}</span>
                    <span class="tag">📈 {s.impact_estimate} Impact</span>
                    <span class="tag">🔧 {s.implementation_difficulty} Effort</span>
                </div>
            </div>""", unsafe_allow_html=True)

        st.markdown("<br>", unsafe_allow_html=True)
        report_txt = (
            f"ATS RESUME ANALYZER — SUGGESTIONS\n{'='*50}\n"
            f"Score: {score}/100\n\n"
            + '\n'.join(
                f"{i+1}. [{s.category.upper()}] {s.suggestion}\n"
                f"   Impact: {s.impact_estimate} | Effort: {s.implementation_difficulty}"
                for i, s in enumerate(suggestions)
            )
        )
        st.download_button("⬇️ Download Suggestions", data=report_txt,
                           file_name="ats_suggestions.txt", mime="text/plain")

    # ── TAB 4: GENERATE CONTENT ────────────────────────────────────────────
    with tab_gen:
        st.markdown("**Generate or improve any resume section:**")
        st.markdown("<br>", unsafe_allow_html=True)

        miss_secs = r['completeness'].missing_sections
        all_secs  = ['summary', 'skills', 'projects', 'certifications', 'experience']

        col_sel, col_role = st.columns(2)
        with col_sel:
            selected = st.selectbox(
                "Section to generate",
                options=all_secs,
                format_func=lambda x: f"{'⚠️ ' if x in miss_secs else '✏️ '}{x.title()}"
            )
        with col_role:
            target_role = st.text_input("Target role", placeholder="ML Engineer Intern, Data Scientist...")

        _, btn_col, _ = st.columns([1, 1, 1])
        with btn_col:
            gen_clicked = st.button("✨ Generate", use_container_width=True)

        if gen_clicked and selected:
            clean_role = target_role.strip() or "ML Engineer Intern"
            with st.spinner("Generating..."):
                suggester = r['suggester']
                resume = r['resume_text']
                jd = r['job_desc']
                mode_str = st.session_state.candidate_mode

                if suggester.model:
                    prompts = {
                        'summary': (
                            f"Write an improved professional summary for this resume targeting: {clean_role}.\n\n"
                            f"RESUME:\n{resume[:2000]}\n\n"
                            f"Rules:\n"
                            f"- 3-4 sentences, under 80 words\n"
                            f"- Reference the candidate's REAL projects and actual skills\n"
                            f"- Include 2-3 keywords from JD: {jd[:300]}\n"
                            f"- No clichés (not 'passionate', 'results-driven')\n"
                            f"- No placeholders like [Your University]\n"
                            f"Return ONLY the summary paragraph."
                        ),
                        'skills': (
                            f"Improve this resume's skills section for role: {clean_role}.\n\n"
                            f"CURRENT RESUME:\n{resume[:2000]}\n\n"
                            f"JOB DESCRIPTION:\n{jd[:600]}\n\n"
                            f"Instructions:\n"
                            f"1. Keep ALL existing skill categories and their items\n"
                            f"2. ADD at least 3-5 missing JD keywords to the right categories\n"
                            f"3. The result MUST contain more items than the original\n"
                            f"Return ONLY lines in format: Category Name: item1, item2, item3"
                        ),
                        'projects': (
                            f"REWRITE and IMPROVE the project descriptions from this resume for role: {clean_role}.\n\n"
                            f"ORIGINAL PROJECTS:\n{resume[:2500]}\n\n"
                            f"JD KEYWORDS TO INCORPORATE: {jd[:400]}\n\n"
                            f"Requirements:\n"
                            f"- Keep the SAME project names and tech stacks\n"
                            f"- Rewrite EVERY bullet to be stronger — stronger verbs, more specific metrics\n"
                            f"- Each bullet must start with an action verb\n"
                            f"- Incorporate relevant JD keywords naturally\n"
                            f"- Add a 'Key Achievement' line for each project if missing\n"
                            f"- The output MUST differ significantly from the input\n\n"
                            f"Format:\n"
                            f"**ProjectName** | TechStack | DateRange\n"
                            f"- Bullet 1 (action verb + metric + JD keyword)\n"
                            f"- Bullet 2\n"
                            f"- Bullet 3\n\n"
                            f"Return ONLY the improved project entries."
                        ),
                        'certifications': (
                            f"Recommend 4-5 specific, real certifications for someone targeting: {clean_role}.\n"
                            f"JD context: {jd[:400]}\n\n"
                            f"For each:\n"
                            f"**Certification Name** | Platform | ~Duration\n"
                            f"Why: one sentence on relevance\n\n"
                            f"Focus on Google, Coursera/DeepLearning.AI, AWS, Kaggle.\n"
                            f"Return ONLY the certification list."
                        ),
                        'experience': (
                            f"Write 2 strong internship/project experience entries for a {mode_str} "
                            f"targeting {clean_role}.\n"
                            f"Resume context:\n{resume[:1500]}\n\n"
                            f"Use this format:\n"
                            f"**Role** | Company | Start – End\n"
                            f"- Achievement bullet with metric\n"
                            f"- Technical contribution bullet\n\n"
                            f"Return ONLY the experience entries."
                        ),
                    }
                    prompt = prompts.get(selected, prompts['summary'])
                    try:
                        generated = suggester._call_model(prompt)
                    except Exception as e:
                        generated = f"❌ AI error: {e}"
                else:
                    # No AI — give a useful structured template, not raw resume dump
                    generated = suggester.generate_content_for_section(
                        selected, {
                            'job_desc': jd, 'existing_resume': resume,
                            'target_role': clean_role,
                            'candidate_mode': st.session_state.candidate_mode
                        }
                    )
                st.session_state.generated_sections[selected] = generated

        if selected in st.session_state.generated_sections:
            content = st.session_state.generated_sections[selected]
            st.markdown(f"**✨ Improved {selected.title()} Section:**")
            # Render with proper markdown formatting
            st.markdown(content)
            st.markdown("<br>", unsafe_allow_html=True)
            c1, c2 = st.columns(2)
            with c1:
                st.download_button(
                    f"⬇️ Download as .txt",
                    data=content,
                    file_name=f"improved_{selected}.txt",
                    mime="text/plain",
                    use_container_width=True
                )
            with c2:
                if st.button("🗑️ Clear", key=f"clear_gen_{selected}", use_container_width=True):
                    del st.session_state.generated_sections[selected]
                    st.rerun()

    # ── FULL REPORT DOWNLOAD ───────────────────────────────────────────────
    st.markdown('<div class="neon-divider"></div>', unsafe_allow_html=True)
    _, dl_col, _ = st.columns([1, 1, 1])
    with dl_col:
        full_report = (
            f"ATS RESUME ANALYSIS REPORT\n{'='*60}\n"
            f"Score: {score}/100 | Mode: {mode}\n\n"
            f"MISSING KEYWORDS:\n"
            + '\n'.join(f"  [{k.category}] {k.term}" for k in r['ranked_keywords'][:20])
            + f"\n\nSECTION SCORES:\n"
            + '\n'.join(f"  {s.section_name}: {s.score}/100" for s in r['section_scores'].values())
            + f"\n\nMISSING SECTIONS:\n"
            + '\n'.join(f"  - {s}" for s in r['completeness'].missing_sections)
            + "\n\nSUGGESTIONS:\n"
            + '\n'.join(f"  {i+1}. {s.suggestion}" for i, s in enumerate(r['suggestions']))
        )
        st.download_button("📥 Full Report", data=full_report,
                           file_name="ats_full_report.txt", mime="text/plain",
                           use_container_width=True)

# ── EMPTY STATE ────────────────────────────────────────────────────────────────
if not st.session_state.analysis_done:
    st.markdown("<br>", unsafe_allow_html=True)
    cols = st.columns(3)
    features = [
        ("⚡", "ATS Score", "TF-IDF similarity scoring against the job description"),
        ("🔍", "Keyword Gaps", "Identifies missing technical terms ranked by importance"),
        ("🤖", "AI Suggestions", "Gemini-powered recommendations to boost your score"),
    ]
    for col, (icon, title, desc) in zip(cols, features):
        with col:
            st.markdown(f"""
            <div style='background:#111125;border:1px solid #1e1e35;border-radius:16px;
                        padding:1.5rem;text-align:center;height:150px'>
                <div style='font-size:1.8rem'>{icon}</div>
                <div style='font-weight:700;color:#c8c8ff;margin:0.4rem 0;font-size:0.9rem'>{title}</div>
                <div style='color:#5a5a7a;font-size:0.78rem;line-height:1.5'>{desc}</div>
            </div>""", unsafe_allow_html=True)

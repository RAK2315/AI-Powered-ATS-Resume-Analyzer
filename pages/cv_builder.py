"""CV Builder — live preview, AI rewrites, dark/light toggle."""

import streamlit as st
import streamlit.components.v1 as components
from components.cv_generator import generate_resume_pdf
from components.resume_extractor import extract_resume_structure, ParsedResume


# ── tiny helpers ──────────────────────────────────────────────────────────────
def _tip(text):
    st.markdown(f"<div style='font-size:0.78rem;color:#5a5a7a;margin:-0.2rem 0 0.6rem'>💡 {text}</div>",
                unsafe_allow_html=True)

def _div():
    st.markdown('<hr style="border:none;border-top:1px solid #1e1e40;margin:1rem 0">', unsafe_allow_html=True)

def ss(key, fallback=""):
    return st.session_state.get(key, fallback) or fallback


# ── AI rewrite button with mode selector ─────────────────────────────────────
_AI_MODES = {
    "rewrite": "✨ Rewrite & improve",
    "expand":  "➕ Add 2 more bullet points",
    "ats":     "🎯 Optimize for ATS keywords",
    "concise": "✂️ Make more concise",
}

def _ai_btn(label, key, current_text, job_desc, mode, suggester):
    """AI rewrite button — always visible, shows appropriate error on click."""
    rkey = f"air_{key}"
    mkey = f"aim_{key}"
    c_sel, c_btn = st.columns([2, 1])
    with c_sel:
        chosen = st.selectbox("AI action", list(_AI_MODES.keys()),
                              format_func=lambda x: _AI_MODES[x],
                              key=mkey, label_visibility="collapsed")
    with c_btn:
        run = st.button("✨ Run AI", key=f"btn_{key}", use_container_width=True)

    if run:
        # Check API key
        no_ai = not suggester or not suggester.has_ai
        if no_ai:
            st.warning("⚠️ Add GEMINI_API_KEY or GROQ_API_KEY to .env to use AI features. Get Groq free at console.groq.com")
            return
        if not current_text or len(current_text.strip()) < 3:
            st.warning("Add some content first, then use AI to improve it.")
            return
        role = ss('cv_target_role') or 'the target role'

        # Detect section type for context-appropriate prompt
        is_skills = 'skills' in key
        is_edu    = 'edu_' in key

        if is_skills:
            instructions = {
                "rewrite": f"Improve this skills section for {role}. Keep existing items, add 2-3 missing JD keywords.",
                "expand":  f"Keep all existing skills AND add a new relevant category for {role} if warranted.",
                "ats":     f"Add keywords from this JD that are missing: {job_desc[:300]}",
                "concise": "Remove any redundant or weak items. Keep only the strongest per category.",
            }
        elif is_edu:
            instructions = {
                "rewrite": f"Write 1-2 concise sentences summarizing this education for {role}. Max 40 words.",
                "expand":  f"Add 1 relevant coursework or achievement sentence for {role}. Factual only, 1 sentence.",
                "ats":     f"Rewrite to include relevant keywords for {role}: {job_desc[:150]}",
                "concise": "Shorten to degree, institution, and one key achievement only.",
            }
        else:
            instructions = {
                "rewrite": f"Rewrite and improve this content for a {role} role. Keep all real facts, names, metrics.",
                "expand":  f"Keep existing content AND add exactly 2 strong new bullet points relevant to {role}.",
                "ats":     f"Rewrite incorporating these ATS keywords naturally: {job_desc[:300]}",
                "concise": "Make each bullet more concise — under 15 words. Preserve all key metrics.",
            }

        with st.spinner(_AI_MODES[chosen] + "..."):
            try:
                if is_skills:
                    prompt = (
                        f"You are a resume skills editor.\n\nTASK: {instructions[chosen]}\n\n"
                        f"CURRENT SKILLS:\n{current_text}\n\n"
                        f"TARGET ROLE: {role}\n\n"
                        f"Rules:\n"
                        f"- Return ONLY lines in format: Category: item1, item2, item3\n"
                        f"- One category per line, no bullets, no sentences, no paragraphs\n"
                        f"- Do NOT invent fake metrics or percentages\n"
                        f"- Keep all existing categories intact"
                    )
                elif is_edu:
                    edu_instructions = {
                        "rewrite": (
                            f"Rewrite the Relevant Coursework for this education entry to be more impactful for {role}.\n"
                            f"Keep it as a comma-separated list of course names. "
                            f"Add 2-3 relevant courses from the JD if they are plausibly part of a CS degree. "
                            f"Remove weak/generic ones. Return ONLY the improved coursework list, no label."
                        ),
                        "expand": (
                            f"Add 2-3 more relevant courses to this coursework list for {role}: {current_text}\n"
                            f"Return ONLY the full updated comma-separated coursework list."
                        ),
                        "ats": (
                            f"Add JD-relevant coursework to this education for {role}. "
                            f"JD context: {job_desc[:200]}\nReturn ONLY the updated coursework list."
                        ),
                        "concise": (
                            f"Shorten to only the 5-6 most relevant courses for {role}: {current_text}\n"
                            f"Return ONLY the shortened comma-separated list."
                        ),
                    }
                    prompt = (
                        f"You are a resume editor.\n\n"
                        f"EDUCATION ENTRY:\n{current_text}\n\n"
                        f"TARGET ROLE: {role}\n\n"
                        f"TASK: {edu_instructions.get(chosen, edu_instructions['rewrite'])}\n\n"
                        f"Rules:\n"
                        f"- Use only real facts, no invented metrics\n"
                        f"- Keep output SHORT and specific\n"
                        f"- No extra explanation, no labels"
                    )
                else:
                    is_summary = key == 'summary'
                    if is_summary:
                        prompt = (
                            f"You are an ATS resume expert.\n\nTASK: {instructions[chosen]}\n\n"
                            f"CURRENT SUMMARY:\n{current_text}\n\n"
                            f"TARGET ROLE: {role}\n\n"
                            f"Rules:\n"
                            f"- Write as a flowing paragraph — ABSOLUTELY NO bullet points\n"
                            f"- 2-3 sentences, under 60 words total\n"
                            f"- Tone: if role has 'intern' or target looks like fresher role → start with "
                            f"'CS/ML student with...' or 'Final-year student...'\n"
                            f"- Use REAL facts from the current summary\n"
                            f"- No clichés: not 'highly skilled', 'passionate', 'dynamic', 'results-driven'\n"
                            f"- Return ONLY the paragraph, no label, no quotes"
                        )
                    else:
                        prompt = (
                            f"You are an ATS resume expert.\n\nTASK: {instructions[chosen]}\n\n"
                            f"CONTENT TO IMPROVE:\n{current_text}\n\n"
                            f"RESUME CONTEXT: {ss('cv_summary') or 'ML/CS student with projects'}\n"
                            f"TARGET ROLE: {role}\n\n"
                            f"Rules:\n"
                            f"- Return ONLY improved bullet points, no extra explanation\n"
                            f"- Keep real project names, real metrics from the original\n"
                            f"- Do NOT invent fake metrics (no '40% improvement' unless in original)\n"
                            f"- Each bullet starts with a strong action verb"
                        )
                result = suggester._call_model(prompt)
                st.session_state[rkey] = result
            except Exception as e:
                err = str(e)
                if 'quota' in err.lower() or '429' in err:
                    st.error("⏳ Quota exceeded. Add GROQ_API_KEY to .env for unlimited free access (console.groq.com)")
                else:
                    st.error(f"AI error: {err[:200]}")

    if rkey in st.session_state:
        st.markdown(
            f"<div style='background:#0d1a2a;border:1px solid #1a3050;border-left:3px solid #00d4ff;"
            f"border-radius:8px;padding:0.8rem;font-family:Space Mono,monospace;font-size:0.8rem;"
            f"line-height:1.7;color:#a0c8e0;white-space:pre-wrap;margin:0.4rem 0'>"
            f"{st.session_state[rkey]}</div>", unsafe_allow_html=True)
        c1, c2 = st.columns(2)
        with c1:
            st.download_button("⬇️ Copy / Download", data=st.session_state[rkey],
                               file_name=f"{key}.txt", mime="text/plain",
                               key=f"dl_{key}", use_container_width=True)
        with c2:
            if st.button("✕ Dismiss", key=f"dis_{key}", use_container_width=True):
                del st.session_state[rkey]; st.rerun()


# ── pre-fill from resume ──────────────────────────────────────────────────────
def _init_from_resume(parsed: ParsedResume):
    for k, v in [('cv_name', parsed.name), ('cv_tagline', parsed.tagline),
                 ('cv_email', parsed.email), ('cv_phone', parsed.phone),
                 ('cv_location', parsed.location), ('cv_linkedin', parsed.linkedin),
                 ('cv_github', parsed.github), ('cv_summary', parsed.summary)]:
        if v:
            st.session_state[k] = v
    if parsed.experiences:
        st.session_state.cv_exp_count = len(parsed.experiences)
        for i, e in enumerate(parsed.experiences):
            st.session_state[f'cv_etitle_{i}'] = e.get('title', '')
            st.session_state[f'cv_ecomp_{i}']  = e.get('company', '')
            st.session_state[f'cv_eloc_{i}']   = e.get('location', '')
            st.session_state[f'cv_estart_{i}'] = e.get('start', '')
            st.session_state[f'cv_eend_{i}']   = e.get('end', '')
            st.session_state[f'cv_ebullets_{i}'] = '\n'.join(e.get('bullets', []))
    if parsed.projects:
        st.session_state.cv_proj_count = len(parsed.projects)
        for i, p in enumerate(parsed.projects):
            st.session_state[f'cv_pname_{i}']    = p.get('name', '')
            st.session_state[f'cv_ptech_{i}']    = p.get('tech', '')
            st.session_state[f'cv_plink_{i}']    = p.get('link', '')
            st.session_state[f'cv_pstart_{i}']   = p.get('start', '')
            st.session_state[f'cv_pend_{i}']     = p.get('end', '')
            st.session_state[f'cv_pbullets_{i}'] = '\n'.join(p.get('bullets', []))
    if parsed.skills:
        st.session_state.cv_skill_rows = [
            {'cat': s.get('category', ''), 'items': s.get('items', '')}
            for s in parsed.skills if s.get('category')
        ]
    if parsed.educations:
        st.session_state.cv_edu_count = len(parsed.educations)
        for i, edu in enumerate(parsed.educations):
            st.session_state[f'cv_edeg_{i}']     = edu.get('degree', '')
            st.session_state[f'cv_einst_{i}']    = edu.get('institution', '')
            st.session_state[f'cv_eloc2_{i}']    = edu.get('location', '')
            st.session_state[f'cv_estart2_{i}']  = edu.get('start', '')
            st.session_state[f'cv_eend2_{i}']    = edu.get('end', '')
            st.session_state[f'cv_egpa_{i}']     = edu.get('gpa', '')
            st.session_state[f'cv_ecourses_{i}'] = edu.get('courses', '')
    if parsed.certifications:
        st.session_state['cv_certs'] = '\n'.join(parsed.certifications)


# ── collect all form data ─────────────────────────────────────────────────────
def _collect_all() -> dict:
    experiences = []
    for i in range(st.session_state.cv_exp_count):
        t = ss(f"cv_etitle_{i}"); c = ss(f"cv_ecomp_{i}")
        if not t and not c: continue
        experiences.append({
            'title': t, 'company': c, 'location': ss(f"cv_eloc_{i}"),
            'start': ss(f"cv_estart_{i}"), 'end': ss(f"cv_eend_{i}"),
            'bullets': [l.strip() for l in ss(f"cv_ebullets_{i}").split('\n') if l.strip()],
        })
    projects = []
    for i in range(st.session_state.cv_proj_count):
        n = ss(f"cv_pname_{i}")
        if not n: continue
        projects.append({
            'name': n, 'tech': ss(f"cv_ptech_{i}"), 'link': ss(f"cv_plink_{i}"),
            'start': ss(f"cv_pstart_{i}"), 'end': ss(f"cv_pend_{i}"),
            'bullets': [l.strip() for l in ss(f"cv_pbullets_{i}").split('\n') if l.strip()],
        })
    skills = [{'category': r['cat'], 'items': r['items']}
              for r in st.session_state.cv_skill_rows if r['cat'] and r['items']]
    educations = []
    for i in range(st.session_state.cv_edu_count):
        d = ss(f"cv_edeg_{i}"); inst = ss(f"cv_einst_{i}")
        if not d and not inst: continue
        educations.append({
            'degree': d, 'institution': inst, 'location': ss(f"cv_eloc2_{i}"),
            'start': ss(f"cv_estart2_{i}"), 'end': ss(f"cv_eend2_{i}"),
            'gpa': ss(f"cv_egpa_{i}"), 'courses': ss(f"cv_ecourses_{i}"),
        })
    return {
        'name': ss("cv_name"), 'tagline': ss("cv_tagline"),
        'email': ss("cv_email"), 'phone': ss("cv_phone"),
        'location': ss("cv_location"), 'linkedin': ss("cv_linkedin"),
        'github': ss("cv_github"), 'summary': ss("cv_summary"),
        'experiences': experiences, 'projects': projects,
        'skills': skills, 'educations': educations,
        'certifications': [c.strip() for c in ss("cv_certs").split('\n') if c.strip()],
    }


# ── live preview HTML ─────────────────────────────────────────────────────────
def _build_preview_html(data: dict, dark: bool = False) -> str:
    bg   = '#1a1a2e' if dark else '#ffffff'
    text = '#e0e0ff' if dark else '#1a1a2e'
    muted= '#8888aa' if dark else '#555577'
    acc  = '#00d4ff' if dark else '#2563EB'
    bdr  = '#2a2a4a' if dark else '#e5e7eb'
    
    def esc(s): return (s or '').replace('&','&amp;').replace('<','&lt;').replace('>','&gt;')

    name    = esc(data.get('name','Your Name'))
    tagline = esc(data.get('tagline',''))
    contact = '  ·  '.join(filter(None, [
        esc(data.get('email','')), esc(data.get('phone','')),
        esc(data.get('location','')), esc(data.get('linkedin','')),
        esc(data.get('github',''))
    ]))

    html = f"""<div style='font-family:Georgia,serif;font-size:11.5px;line-height:1.55;
                           color:{text};background:{bg};padding:1.4rem 1.6rem;min-height:100%'>
      <div style='text-align:center;border-bottom:2px solid {acc};padding-bottom:0.5rem;margin-bottom:0.6rem'>
        <div style='font-size:1.35rem;font-weight:700;color:{text}'>{name}</div>
        {'<div style="color:'+muted+';font-size:0.83rem;margin-top:2px">'+tagline+'</div>' if tagline else ''}
        {'<div style="color:'+muted+';font-size:0.72rem;margin-top:3px">'+contact+'</div>' if contact else ''}
      </div>"""

    def sec(title):
        return (f"<div style='font-size:0.65rem;font-weight:700;color:{acc};letter-spacing:0.1em;"
                f"text-transform:uppercase;border-bottom:1px solid {bdr};margin:0.7rem 0 0.3rem;"
                f"padding-bottom:2px'>{title}</div>")

    if data.get('summary'):
        html += sec('Professional Summary')
        html += f"<div style='font-size:0.76rem;color:{text}'>{esc(data['summary'])}</div>"

    exps = data.get('experiences', [])
    if exps:
        html += sec('Work Experience')
        for exp in exps:
            t = esc(exp.get('title','')); co = esc(exp.get('company',''))
            s = esc(exp.get('start','')); e = esc(exp.get('end',''))
            date = f"{s} – {e}" if s else e
            html += f"<div style='display:flex;justify-content:space-between'><b style='font-size:0.78rem'>{t}</b><span style='color:{muted};font-size:0.7rem'>{date}</span></div>"
            html += f"<div style='color:{muted};font-style:italic;font-size:0.72rem;margin-bottom:2px'>{co}</div>"
            for b in exp.get('bullets', []):
                html += f"<div style='padding-left:0.7rem;font-size:0.72rem;color:{text}'>- {esc(b)}</div>"
            html += "<div style='height:0.3rem'></div>"

    projs = data.get('projects', [])
    if projs:
        html += sec('Projects')
        for p in projs:
            pn = esc(p.get('name','')); pt = esc(p.get('tech',''))
            ps = esc(p.get('start','')); pe = esc(p.get('end',''))
            date = f"{ps} – {pe}" if ps else pe
            if pn:
                tech_part = f" <span style='color:{muted}'>| {pt}</span>" if pt else ''
                date_part = f"<span style='color:{muted};font-size:0.7rem;float:right'>{date}</span>" if date else ''
                html += f"<div style='font-weight:600;font-size:0.78rem'>{pn}{tech_part}{date_part}</div>"
                for b in p.get('bullets', []):
                    html += f"<div style='padding-left:0.7rem;font-size:0.72rem;color:{text}'>- {esc(b)}</div>"
                link = p.get('link', '')
                if link:
                    html += f"<div style='padding-left:0.7rem;font-size:0.7rem;color:{acc}'>{esc(link)}</div>"
                html += "<div style='height:0.3rem'></div>"

    skills = data.get('skills', [])
    if skills:
        html += sec('Skills')
        for s in skills:
            cat = esc(s.get('category','')); items = esc(s.get('items',''))
            if cat and items:
                html += f"<div style='font-size:0.73rem;margin-bottom:2px'><b>{cat}:</b> {items}</div>"

    edus = data.get('educations', [])
    if edus:
        html += sec('Education')
        for edu in edus:
            deg  = esc(edu.get('degree',''))
            inst = esc(edu.get('institution',''))
            loc  = esc(edu.get('location',''))
            gpa  = esc(edu.get('gpa',''))
            s    = esc(edu.get('start','')); e = esc(edu.get('end',''))
            courses = esc(edu.get('courses',''))
            date = f"{s} – {e}" if s else e
            if deg or inst:
                html += f"<div style='display:flex;justify-content:space-between'><b style='font-size:0.78rem'>{deg}</b><span style='color:{muted};font-size:0.7rem'>{date}</span></div>"
                meta = inst + (f", {loc}" if loc else '') + (f" · GPA: {gpa}" if gpa else '')
                html += f"<div style='color:{muted};font-style:italic;font-size:0.72rem'>{meta}</div>"
                if courses:
                    html += f"<div style='font-size:0.7rem;color:{muted};margin-top:2px'>Coursework: {courses}</div>"
                html += "<div style='height:0.3rem'></div>"

    certs = data.get('certifications', [])
    if certs:
        html += sec('Certifications & Awards')
        for c in certs:
            html += f"<div style='font-size:0.73rem;color:{text}'>- {esc(c)}</div>"

    html += "</div>"
    return html


# ══════════════════════════════════════════════════════════════════════════════
# MAIN
# ══════════════════════════════════════════════════════════════════════════════
def render_cv_builder(gemini_key: str = ""):
    from components.ai_suggester import AISuggester
    import os
    from dotenv import load_dotenv
    import pathlib
    # Re-read env at runtime so the key is fresh (handles local .env files)
    _base = pathlib.Path(__file__).parent.parent
    for _f in ['.env', '.env.local']:
        fp = _base / _f
        if fp.exists():
            load_dotenv(fp, override=True)
            break
    _live_key = os.getenv("GEMINI_API_KEY", "").strip().strip('"').strip("'")
    _bad = ("", "your_key_here", "AIza...", "your-key-here", "your_api_key_here")
    if _live_key in _bad or len(_live_key) < 20:
        _live_key = gemini_key  # fall back to passed key
    # Also try Streamlit secrets
    if not _live_key:
        try:
            import streamlit as _st
            _live_key = _st.secrets.get("GEMINI_API_KEY", "").strip().strip('"').strip("'")
            if _live_key in _bad or len(_live_key) < 20:
                _live_key = ""
        except Exception:
            pass
    # Also load Groq key for Llama fallback
    _groq_key = os.getenv("GROQ_API_KEY", "").strip().strip('"').strip("'")
    _groq_bad = ("", "your_groq_key_here", "gsk_...")
    if _groq_key in _groq_bad or len(_groq_key) < 20:
        _groq_key = ""
    if not _groq_key:
        try:
            import streamlit as _st2
            _groq_key = _st2.secrets.get("GROQ_API_KEY", "").strip().strip('"').strip("'")
            if _groq_key in _groq_bad or len(_groq_key) < 20:
                _groq_key = ""
        except Exception:
            pass
    suggester = AISuggester(api_key=_live_key or None, groq_key=_groq_key or None)

    # session state defaults
    for k, v in [('cv_exp_count', 1), ('cv_proj_count', 2), ('cv_edu_count', 1),
                 ('cv_pdf_bytes', None), ('cv_pdf_name', ''),
                 ('cv_prefilled', False), ('cv_target_role', ''),
                 ('cv_preview_dark', False)]:
        if k not in st.session_state:
            st.session_state[k] = v

    if 'cv_skill_rows' not in st.session_state:
        # Start blank — auto-fill will populate from resume if user uploads one
        st.session_state.cv_skill_rows = []

    has_results = st.session_state.get('results') is not None
    resume_text = st.session_state['results']['resume_text'] if has_results else ""
    job_desc    = st.session_state['results']['job_desc']    if has_results else ""
    mode        = st.session_state.get('candidate_mode', '🎓 Student / Fresher')

    # Apply pre-parsed data from "Implement All" button
    impl_parsed = st.session_state.pop('_impl_parsed', None)
    if impl_parsed:
        from components.resume_extractor import ParsedResume
        _init_from_resume(impl_parsed)
        st.success("✅ Resume imported to CV Builder! Review and edit below.")

    # Apply pending keywords from "Quick Add" button on Keywords tab
    pending_kws = st.session_state.pop('pending_keywords', None)
    if pending_kws:
        rows = st.session_state.cv_skill_rows
        # Find a "technical" or "ML" row to append to, else create new row
        added = []
        for kw in pending_kws:
            placed = False
            for row in rows:
                cat_l = row['cat'].lower()
                kw_l = kw.lower()
                if kw_l not in row['items'].lower():
                    # Match to right category
                    is_lang = kw_l in {'python','java','c++','r','scala','golang','rust','sql','c'}
                    is_lib  = kw_l in {'pytorch','tensorflow','keras','numpy','pandas','scikit-learn',
                                       'streamlit','fastapi','matplotlib','xgboost','lightgbm','scipy'}
                    is_cloud= kw_l in {'aws','gcp','azure','docker','kubernetes','spark'}
                    if is_lang and 'lang' in cat_l:
                        row['items'] = row['items'].rstrip(', ') + f', {kw}'
                        placed = True; break
                    elif is_lib and ('lib' in cat_l or 'tool' in cat_l or 'frame' in cat_l):
                        row['items'] = row['items'].rstrip(', ') + f', {kw}'
                        placed = True; break
                    elif is_cloud and ('cloud' in cat_l or 'tool' in cat_l or 'dev' in cat_l):
                        row['items'] = row['items'].rstrip(', ') + f', {kw}'
                        placed = True; break
                    elif not is_lang and not is_lib and not is_cloud:
                        # General skill — add to AI/ML or first non-lang row
                        if 'ai' in cat_l or 'ml' in cat_l or 'machine' in cat_l or 'data' in cat_l:
                            row['items'] = row['items'].rstrip(', ') + f', {kw}'
                            placed = True; break
            if not placed:
                added.append(kw)
        if added:
            # Add remaining as a new row if not already present
            existing_items = ' '.join(r['items'].lower() for r in rows)
            new_items = ', '.join(k for k in added if k.lower() not in existing_items)
            if new_items:
                rows.append({'cat': 'Additional Skills', 'items': new_items})
        st.session_state.cv_skill_rows = rows
        st.success(f"✅ Added {len(pending_kws)} keywords from your analysis to Skills section!")

    # ── layout ────────────────────────────────────────────────────────────────
    col_form, col_prev = st.columns([3, 2], gap="large")

    with col_form:
        # Header + dark/light toggle on same row
        h1, h2 = st.columns([4, 1])
        with h1:
            st.markdown("""
            <div style='padding:0.3rem 0 0.2rem'>
              <div style='font-size:1.7rem;font-weight:800;
                          background:linear-gradient(135deg,#00d4ff,#7b2fff);
                          -webkit-background-clip:text;-webkit-text-fill-color:transparent;
                          background-clip:text'>Resume Builder</div>
              <div style='color:#5a5a7a;font-family:Space Mono,monospace;font-size:0.75rem'>
                Fill in details → live preview → download PDF
              </div>
            </div>""", unsafe_allow_html=True)
        with h2:
            st.markdown("<div style='height:0.8rem'></div>", unsafe_allow_html=True)
            dark = st.toggle("🌙", value=st.session_state.cv_preview_dark,
                             key="cv_preview_dark",
                             help="Toggle preview dark/light mode")

        _div()

        # auto-fill banner
        if has_results and not st.session_state.cv_prefilled:
            st.markdown("""
            <div style='background:rgba(0,212,255,0.08);border:1px solid rgba(0,212,255,0.25);
                        border-radius:10px;padding:0.7rem 1rem;margin-bottom:0.8rem'>
              <b style='color:#00d4ff'>📄 Resume detected!</b>
              <span style='color:#8888a8;font-size:0.85rem'> Auto-fill this form from your uploaded resume.</span>
            </div>""", unsafe_allow_html=True)
            c1, c2, _ = st.columns([1, 1, 2])
            with c1:
                if st.button("⚡ Auto-fill from Resume", use_container_width=True):
                    with st.spinner("Parsing..."):
                        parsed = extract_resume_structure(resume_text, suggester.model)
                        _init_from_resume(parsed)
                        st.session_state.cv_prefilled = True
                        st.rerun()
            with c2:
                if st.button("Start Blank", use_container_width=True):
                    st.session_state.cv_prefilled = True
                    st.rerun()
            st.stop()
        elif has_results:
            with st.expander("🔄 Re-parse from uploaded resume"):
                if st.button("Re-fill all fields", use_container_width=True):
                    with st.spinner("Re-parsing..."):
                        parsed = extract_resume_structure(resume_text, suggester.model)
                        _init_from_resume(parsed)
                        st.rerun()

        st.text_input("🎯 Target Role", key="cv_target_role",
                      placeholder="ML Engineer Intern, Data Scientist...")
        _div()

        # ── PERSONAL INFO ─────────────────────────────────────────────────────
        st.markdown("### 👤 Personal Information")
        c1, c2 = st.columns(2)
        with c1:
            st.text_input("Full Name *",     key="cv_name",     placeholder="Rehaan Ahmad Khan")
            st.text_input("Email *",         key="cv_email",    placeholder="you@email.com")
            st.text_input("Location",        key="cv_location", placeholder="Greater Noida, India")
        with c2:
            st.text_input("Title / Tagline", key="cv_tagline",  placeholder="CS Student | Aspiring ML Engineer")
            st.text_input("Phone",           key="cv_phone",    placeholder="+91 98765 43210")
            st.text_input("LinkedIn",        key="cv_linkedin", placeholder="linkedin.com/in/yourname")
        st.text_input("GitHub",              key="cv_github",   placeholder="github.com/yourusername")
        _div()

        # ── SUMMARY ───────────────────────────────────────────────────────────
        st.markdown("### 📝 Professional Summary")
        _tip("3-4 sentences: who you are, top skills, what you seek.")
        st.text_area("Professional Summary", height=90, key="cv_summary", label_visibility="collapsed",
                     placeholder="CS (AI-ML) student with hands-on ML project experience...")
        _ai_btn("Summary", "summary", ss("cv_summary"), job_desc, mode, suggester)
        _div()

        # ── WORK EXPERIENCE ───────────────────────────────────────────────────
        st.markdown("### 💼 Work Experience")
        _tip("Internships count. Leave blank if none.")
        ca, cb, _ = st.columns([1, 1, 4])
        with ca:
            if st.button("＋ Add", key="add_exp"):
                st.session_state.cv_exp_count = min(st.session_state.cv_exp_count + 1, 6); st.rerun()
        with cb:
            if st.button("－ Remove", key="rem_exp"):
                st.session_state.cv_exp_count = max(st.session_state.cv_exp_count - 1, 0); st.rerun()
        for i in range(st.session_state.cv_exp_count):
            label = f"Position {i+1}" + (f": {ss(f'cv_etitle_{i}')} @ {ss(f'cv_ecomp_{i}')}" if ss(f'cv_etitle_{i}') else "")
            with st.expander(label, expanded=(i == 0)):
                e1, e2 = st.columns(2)
                with e1:
                    st.text_input("Job Title",  key=f"cv_etitle_{i}", placeholder="ML Engineer Intern")
                    st.text_input("Company",    key=f"cv_ecomp_{i}",  placeholder="Company Name")
                    st.text_input("Location",   key=f"cv_eloc_{i}",   placeholder="Remote / Noida")
                with e2:
                    st.text_input("Start",      key=f"cv_estart_{i}", placeholder="Jun 2025")
                    st.text_input("End",        key=f"cv_eend_{i}",   placeholder="Aug 2025")
                st.text_area("Achievements (one per line)", key=f"cv_ebullets_{i}", height=90,
                             placeholder="Achieved 92% accuracy on 10,000 samples\nReduced training time by 35%")
                _ai_btn(f"Exp {i+1}", f"exp_{i}", ss(f"cv_ebullets_{i}"), job_desc, mode, suggester)
        _div()

        # ── PROJECTS ──────────────────────────────────────────────────────────
        st.markdown("### 🚀 Projects")
        _tip("Most important section for freshers. Use real metrics.")
        pa, pb, _ = st.columns([1, 1, 4])
        with pa:
            if st.button("＋ Add", key="add_proj"):
                st.session_state.cv_proj_count = min(st.session_state.cv_proj_count + 1, 8); st.rerun()
        with pb:
            if st.button("－ Remove", key="rem_proj"):
                st.session_state.cv_proj_count = max(st.session_state.cv_proj_count - 1, 0); st.rerun()
        for i in range(st.session_state.cv_proj_count):
            pn = ss(f'cv_pname_{i}')
            with st.expander(f"Project {i+1}" + (f": {pn}" if pn else ""), expanded=(i < 2)):
                p1, p2 = st.columns(2)
                with p1:
                    st.text_input("Project Name",  key=f"cv_pname_{i}", placeholder="AI Voice Detection API")
                    st.text_input("Tech Stack",    key=f"cv_ptech_{i}", placeholder="Python, FastAPI, Scikit-learn")
                with p2:
                    st.text_input("GitHub / Link", key=f"cv_plink_{i}", placeholder="github.com/user/project")
                    dc1, dc2 = st.columns(2)
                    with dc1: st.text_input("Start", key=f"cv_pstart_{i}", placeholder="01/2025")
                    with dc2: st.text_input("End",   key=f"cv_pend_{i}",   placeholder="02/2025")
                st.text_area("Description (one point per line)", key=f"cv_pbullets_{i}", height=90,
                             placeholder="Built REST API achieving 99.24% accuracy\nDeployed on Render with <3s latency")
                # Pass the widget value directly from session_state (already set by text_area above)
                _ai_btn(f"Proj {i+1}", f"proj_{i}",
                        st.session_state.get(f"cv_pbullets_{i}", ""),
                        job_desc, mode, suggester)
        _div()

        # ── SKILLS ────────────────────────────────────────────────────────────
        st.markdown("### 🔧 Skills")
        _tip("Each row = one category. ↑↓ reorder. ✕ delete.")
        rows = st.session_state.cv_skill_rows
        changed = False
        for i, row in enumerate(rows):
            cols = st.columns([2, 3, 0.4, 0.4, 0.4])
            with cols[0]:
                new_cat = st.text_input("Cat", key=f"cv_scat_{i}",
                                        value=row['cat'], label_visibility="collapsed",
                                        placeholder="Category")
            with cols[1]:
                new_items = st.text_input("Items", key=f"cv_sitems_{i}",
                                          value=row['items'], label_visibility="collapsed",
                                          placeholder="skill1, skill2, skill3")
            with cols[2]:
                if st.button("↑", key=f"su_{i}", use_container_width=True) and i > 0:
                    rows[i], rows[i-1] = rows[i-1], rows[i]; changed = True
            with cols[3]:
                if st.button("↓", key=f"sd_{i}", use_container_width=True) and i < len(rows)-1:
                    rows[i], rows[i+1] = rows[i+1], rows[i]; changed = True
            with cols[4]:
                if st.button("✕", key=f"sx_{i}", use_container_width=True):
                    rows.pop(i); changed = True; break
            if not changed and i < len(rows):
                rows[i]['cat'] = new_cat; rows[i]['items'] = new_items
        if changed:
            st.session_state.cv_skill_rows = rows; st.rerun()
        if st.button("＋ Add Skill Category", key="add_skill"):
            st.session_state.cv_skill_rows.append({'cat': '', 'items': ''}); st.rerun()

        skill_text = '\n'.join(f"{r['cat']}: {r['items']}" for r in rows if r['cat'])
        _ai_btn("Skills", "skills", skill_text, job_desc, mode, suggester)
        _div()

        # ── EDUCATION ─────────────────────────────────────────────────────────
        st.markdown("### 🎓 Education")
        ea, eb, _ = st.columns([1, 1, 4])
        with ea:
            if st.button("＋ Add", key="add_edu"):
                st.session_state.cv_edu_count = min(st.session_state.cv_edu_count + 1, 4); st.rerun()
        with eb:
            if st.button("－ Remove", key="rem_edu"):
                st.session_state.cv_edu_count = max(st.session_state.cv_edu_count - 1, 1); st.rerun()
        for i in range(st.session_state.cv_edu_count):
            deg = ss(f'cv_edeg_{i}')
            with st.expander(f"Education {i+1}" + (f": {deg}" if deg else ""), expanded=True):
                d1, d2 = st.columns(2)
                with d1:
                    st.text_input("Degree",      key=f"cv_edeg_{i}",    placeholder="B.Tech CS (AI & ML)")
                    st.text_input("Institution", key=f"cv_einst_{i}",   placeholder="JSS University")
                    st.text_input("Location",    key=f"cv_eloc2_{i}",   placeholder="Noida, India")
                with d2:
                    st.text_input("Start",       key=f"cv_estart2_{i}", placeholder="08/2025")
                    st.text_input("End",         key=f"cv_eend2_{i}",   placeholder="Present")
                    st.text_input("GPA/CGPA/%",  key=f"cv_egpa_{i}",    placeholder="8.5 / 10")
                st.text_input("Relevant Coursework", key=f"cv_ecourses_{i}",
                              placeholder="DSA, Python, ML Fundamentals, OOP")
                # AI rewrite for coursework/description
                edu_text = '\n'.join(filter(None, [
                    ss(f"cv_edeg_{i}"), ss(f"cv_einst_{i}"), ss(f"cv_ecourses_{i}")
                ]))
                _ai_btn(f"Education {i+1}", f"edu_{i}", edu_text, job_desc, mode, suggester)
        _div()

        # ── CERTIFICATIONS ────────────────────────────────────────────────────
        st.markdown("### 🏅 Certifications & Awards")
        _tip("One per line. Certs: Name | Platform | Year. Awards: full text.")
        st.text_area("Certifications", height=80, key="cv_certs", label_visibility="collapsed",
                     placeholder="ML Specialization | Coursera | 2025\n1st Runner-Up | India AI Impact Buildathon 2026")

        # Certs AI button — special mode for formatting + suggesting
        certs_text = st.session_state.get("cv_certs", "")
        crkey = "air_certs"
        c_sel, c_btn = st.columns([2, 1])
        with c_sel:
            cert_mode = st.selectbox("AI action", [
                "format",    "suggest",   "rewrite"
            ], format_func=lambda x: {
                "format":  "🗂️ Clean up formatting",
                "suggest": "💡 Suggest certs for my role",
                "rewrite": "✨ Improve award descriptions",
            }[x], key="aim_certs", label_visibility="collapsed")
        with c_btn:
            run_certs = st.button("✨ Run AI", key="btn_certs", use_container_width=True)

        if run_certs:
            if not suggester or not suggester.has_ai:
                st.warning("Add GROQ_API_KEY to .env for AI features.")
            else:
                role = ss('cv_target_role') or 'ML Engineer'
                cert_prompts = {
                    "format": (
                        f"Clean up and standardize the formatting of these certifications/awards:\n\n"
                        f"{certs_text}\n\n"
                        f"Rules:\n"
                        f"- One entry per line\n"
                        f"- Certs format: Certification Name | Platform | Year\n"
                        f"- Awards format: Award Name | Organization | Date | Brief context (1 sentence)\n"
                        f"- Detect where one entry ends and the next begins\n"
                        f"- Fix any run-on text, capitalize properly\n"
                        f"- Return ONLY the cleaned list, one entry per line"
                    ),
                    "suggest": (
                        f"Suggest 4-5 real, obtainable certifications for someone targeting: {role}.\n"
                        f"Existing certs: {certs_text[:300] or 'none'}\n\n"
                        f"Format each as: Certification Name | Platform | ~Time to complete\n"
                        f"Focus on: Google, Coursera/DeepLearning.AI, Kaggle, AWS, Hugging Face.\n"
                        f"Return ONLY the list, one cert per line."
                    ),
                    "rewrite": (
                        f"Improve the descriptions of these awards/certifications for a resume:\n\n"
                        f"{certs_text}\n\n"
                        f"Rules:\n"
                        f"- Make award descriptions more impactful (mention scale, competition size)\n"
                        f"- Certs: keep Name | Platform | Year format\n"
                        f"- Keep all real facts, no invented details\n"
                        f"- Return ONLY the improved list, one per line"
                    ),
                }
                with st.spinner("Running AI on certifications..."):
                    try:
                        result = suggester._call_model(cert_prompts[cert_mode])
                        st.session_state[crkey] = result
                    except Exception as e:
                        st.error(f"AI error: {str(e)[:200]}")

        if crkey in st.session_state:
            st.markdown(
                f"<div style='background:#0d1a2a;border:1px solid #1a3050;border-left:3px solid #00d4ff;"
                f"border-radius:8px;padding:0.8rem;font-family:Space Mono,monospace;font-size:0.8rem;"
                f"line-height:1.8;color:#a0c8e0;white-space:pre-wrap;margin:0.4rem 0'>"
                f"{st.session_state[crkey]}</div>", unsafe_allow_html=True)
            c1, c2 = st.columns(2)
            with c1:
                st.download_button("⬇️ Copy", data=st.session_state[crkey],
                                   file_name="certs.txt", mime="text/plain",
                                   key="dl_certs", use_container_width=True)
            with c2:
                if st.button("✕ Dismiss", key="dis_certs", use_container_width=True):
                    del st.session_state[crkey]; st.rerun()
        _div()

        # ── GENERATE ──────────────────────────────────────────────────────────
        if not ss("cv_name") or not ss("cv_email"):
            st.warning("⚠️ Add at least your **Name** and **Email** to generate.")
        else:
            if st.button("⚡ Generate Resume PDF", use_container_width=True, key="gen_pdf"):
                with st.spinner("Building PDF..."):
                    try:
                        pdf_bytes = generate_resume_pdf(_collect_all())
                        st.session_state.cv_pdf_bytes = pdf_bytes
                        st.session_state.cv_pdf_name = ss("cv_name").replace(' ', '_') + "_Resume.pdf"
                        st.success("✅ Done!")
                    except Exception as e:
                        st.error(f"❌ {e}")
            if st.session_state.cv_pdf_bytes:
                st.download_button("📥 Download Resume PDF",
                                   data=st.session_state.cv_pdf_bytes,
                                   file_name=st.session_state.cv_pdf_name,
                                   mime="application/pdf", use_container_width=True)

    # ── RIGHT PANEL: LIVE PREVIEW ─────────────────────────────────────────────
    with col_prev:
        # Preview header with dark/light label
        mode_label = "🌙 Dark" if st.session_state.cv_preview_dark else "☀️ Light"
        st.markdown(f"""
        <div style='font-size:0.85rem;font-weight:700;color:#c0c0ff;margin-bottom:0.4rem;
                    font-family:Space Mono,monospace;letter-spacing:0.05em'>
            👁 LIVE PREVIEW &nbsp;<span style='font-size:0.7rem;color:#5a5a8a'>{mode_label}</span>
        </div>""", unsafe_allow_html=True)

        preview_data = _collect_all()
        preview_html = _build_preview_html(preview_data, dark=st.session_state.cv_preview_dark)

        bg_wrap = '#0d0d1a' if st.session_state.cv_preview_dark else '#f0f0f8'
        components.html(
            f"""<!DOCTYPE html><html>
            <body style='margin:0;padding:6px;background:{bg_wrap};box-sizing:border-box'>
            <div style='border-radius:8px;overflow:hidden;
                        box-shadow:0 2px 12px rgba(0,0,0,0.3)'>
            {preview_html}
            </div></body></html>""",
            height=750, scrolling=True
        )

        # Checklist
        d = preview_data
        exp_n  = len(d['experiences'])
        proj_n = len(d['projects'])
        skl_n  = len(d['skills'])
        edu_n  = len(d['educations'])
        cert_n = len(d['certifications'])
        has_sum = bool(d.get('summary'))

        st.markdown(f"""
        <div style='background:#0d1a0d;border:1px solid #1a401a;border-radius:8px;
                    padding:0.6rem 0.9rem;margin-top:0.4rem;font-size:0.78rem;
                    color:#80c080;line-height:2'>
            {'✅' if has_sum  else '⚪'} Summary &nbsp;
            {'✅' if exp_n>0  else '⚪'} Experience ({exp_n}) &nbsp;
            {'✅' if proj_n>0 else '⚪'} Projects ({proj_n})<br>
            {'✅' if skl_n>0  else '⚪'} Skills ({skl_n} categories) &nbsp;
            {'✅' if edu_n>0  else '⚪'} Education &nbsp;
            {'✅' if cert_n>0 else '⚪'} Awards/Certs ({cert_n})
        </div>""", unsafe_allow_html=True)

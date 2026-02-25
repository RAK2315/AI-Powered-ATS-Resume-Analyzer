"""
CV Builder Page — fixed version
Data stored in session state so it survives generate-button reruns.
"""

import streamlit as st
from components.cv_generator import generate_resume_pdf


# ── helpers ───────────────────────────────────────────────────────────────────

def _bullets(label: str, key: str, placeholder: str = "One point per line") -> list:
    raw = st.text_area(label, key=key, height=110, placeholder=placeholder)
    return [l.strip() for l in raw.strip().split('\n') if l.strip()]


def _tip(text: str):
    st.markdown(
        f"<div style='font-size:0.78rem;color:#5a5a7a;margin:-0.3rem 0 0.7rem'>💡 {text}</div>",
        unsafe_allow_html=True,
    )


def _divider():
    st.markdown('<div class="neon-divider" style="margin:1.5rem 0"></div>',
                unsafe_allow_html=True)


# ── main ──────────────────────────────────────────────────────────────────────

def render_cv_builder():

    # ── init counters once ────────────────────────────────────────────────────
    for key, default in [('cv_exp_count', 1), ('cv_proj_count', 2),
                         ('cv_skill_count', 4), ('cv_edu_count', 1),
                         ('cv_pdf_bytes', None), ('cv_pdf_name', '')]:
        if key not in st.session_state:
            st.session_state[key] = default

    # ── header ────────────────────────────────────────────────────────────────
    st.markdown("""
    <div style='padding:1.5rem 0 0.5rem'>
        <div style='font-size:2rem;font-weight:800;
                    background:linear-gradient(135deg,#00d4ff,#7b2fff);
                    -webkit-background-clip:text;-webkit-text-fill-color:transparent;
                    background-clip:text;letter-spacing:-0.02em'>Resume Builder</div>
        <div style='color:#7878a0;font-family:Space Mono,monospace;font-size:0.82rem;
                    margin-top:0.3rem'>
            Fill in your details → Download ATS-ready PDF
        </div>
    </div>
    """, unsafe_allow_html=True)
    _divider()

    # ═════════════════════════════════════════════════════════════════════════
    # 1. PERSONAL INFO
    # ═════════════════════════════════════════════════════════════════════════
    st.markdown("### 👤 Personal Information")
    _tip("This becomes your resume header.")

    c1, c2 = st.columns(2)
    with c1:
        name     = st.text_input("Full Name *",            key="cv_name",     placeholder="Rehaan Ahmad Khan")
        email    = st.text_input("Email *",                key="cv_email",    placeholder="you@email.com")
        location = st.text_input("Location",               key="cv_location", placeholder="Greater Noida, India")
    with c2:
        tagline  = st.text_input("Title / Tagline",        key="cv_tagline",  placeholder="B.Tech CS (AI-ML) Student | ML Engineer")
        phone    = st.text_input("Phone",                  key="cv_phone",    placeholder="+91 98765 43210")
        linkedin = st.text_input("LinkedIn URL",           key="cv_linkedin", placeholder="linkedin.com/in/yourname")
    github = st.text_input("GitHub URL", key="cv_github", placeholder="github.com/yourusername")

    _divider()

    # ═════════════════════════════════════════════════════════════════════════
    # 2. SUMMARY
    # ═════════════════════════════════════════════════════════════════════════
    st.markdown("### 📝 Professional Summary")
    _tip("3-4 sentences: who you are, your top skills, what you're seeking.")
    summary = st.text_area(
        "Summary", height=100, key="cv_summary", label_visibility="collapsed",
        placeholder=(
            "B.Tech Computer Science (AI-ML) student at JSS University with hands-on "
            "experience building end-to-end ML pipelines. Proficient in Python, Scikit-learn, "
            "and Streamlit. Seeking Summer 2026 ML internship to apply data science skills "
            "to real-world problems."
        )
    )

    _divider()

    # ═════════════════════════════════════════════════════════════════════════
    # 3. WORK EXPERIENCE
    # ═════════════════════════════════════════════════════════════════════════
    st.markdown("### 💼 Work Experience")
    _tip("Leave blank if you have no work experience — internships count here too.")

    ca, cb, _ = st.columns([1, 1, 4])
    with ca:
        if st.button("＋ Add", key="add_exp", use_container_width=True):
            st.session_state.cv_exp_count = min(st.session_state.cv_exp_count + 1, 6)
            st.rerun()
    with cb:
        if st.button("－ Remove", key="rem_exp", use_container_width=True):
            st.session_state.cv_exp_count = max(st.session_state.cv_exp_count - 1, 0)
            st.rerun()

    for i in range(st.session_state.cv_exp_count):
        with st.expander(f"Position {i+1}", expanded=(i == 0)):
            ec1, ec2 = st.columns(2)
            with ec1:
                st.text_input("Job Title",  key=f"cv_etitle_{i}", placeholder="ML Engineer Intern")
                st.text_input("Company",    key=f"cv_ecomp_{i}",  placeholder="Inficore Soft")
                st.text_input("Location",   key=f"cv_eloc_{i}",   placeholder="Remote / Noida")
            with ec2:
                st.text_input("Start",      key=f"cv_estart_{i}", placeholder="Jun 2025")
                st.text_input("End",        key=f"cv_eend_{i}",   placeholder="Aug 2025")
            _bullets("Achievements (one per line)", key=f"cv_ebullets_{i}",
                     placeholder=(
                         "Achieved 92% accuracy on 10,000-sample dataset using XGBoost\n"
                         "Reduced model training time by 35% through pipeline optimization\n"
                         "Deployed Streamlit web app with sub-2s inference latency"
                     ))

    _divider()

    # ═════════════════════════════════════════════════════════════════════════
    # 4. PROJECTS
    # ═════════════════════════════════════════════════════════════════════════
    st.markdown("### 🚀 Projects")
    _tip("For freshers, projects are your most important section. Use real metrics.")

    pa, pb, _ = st.columns([1, 1, 4])
    with pa:
        if st.button("＋ Add", key="add_proj", use_container_width=True):
            st.session_state.cv_proj_count = min(st.session_state.cv_proj_count + 1, 8)
            st.rerun()
    with pb:
        if st.button("－ Remove", key="rem_proj", use_container_width=True):
            st.session_state.cv_proj_count = max(st.session_state.cv_proj_count - 1, 0)
            st.rerun()

    for i in range(st.session_state.cv_proj_count):
        with st.expander(f"Project {i+1}", expanded=(i < 2)):
            pa1, pa2 = st.columns(2)
            with pa1:
                st.text_input("Project Name", key=f"cv_pname_{i}",
                              placeholder="Glass Transition Temperature Predictor")
                st.text_input("Tech Stack",   key=f"cv_ptech_{i}",
                              placeholder="Python, Scikit-learn, LightGBM, Streamlit")
            with pa2:
                st.text_input("GitHub / Demo Link", key=f"cv_plink_{i}",
                              placeholder="github.com/username/project")
            _bullets("Description (one point per line)", key=f"cv_pbullets_{i}",
                     placeholder=(
                         "Achieved 98.85% accuracy (R²=0.985) on 635 polymer samples\n"
                         "Evaluated 14 regression models: LightGBM, XGBoost, CatBoost, Random Forest\n"
                         "Deployed production Streamlit app reducing testing time from 3h to <1s"
                     ))

    _divider()

    # ═════════════════════════════════════════════════════════════════════════
    # 5. SKILLS
    # ═════════════════════════════════════════════════════════════════════════
    st.markdown("### 🔧 Skills")
    _tip("Use exact keywords from job descriptions. Organize into categories.")

    sa, sb, _ = st.columns([1, 1, 4])
    with sa:
        if st.button("＋ Add", key="add_skill", use_container_width=True):
            st.session_state.cv_skill_count = min(st.session_state.cv_skill_count + 1, 8)
            st.rerun()
    with sb:
        if st.button("－ Remove", key="rem_skill", use_container_width=True):
            st.session_state.cv_skill_count = max(st.session_state.cv_skill_count - 1, 1)
            st.rerun()

    defaults = [
        ("Programming Languages",   "Python, C"),
        ("ML & AI",                 "Machine Learning, Supervised Learning, Model Evaluation, Feature Engineering"),
        ("Libraries & Tools",       "NumPy, Pandas, Scikit-learn, Matplotlib, Seaborn, Streamlit"),
        ("Developer Tools",         "Git, GitHub, VS Code, Jupyter Notebook, Google Colab"),
    ]
    for i in range(st.session_state.cv_skill_count):
        dc, di = defaults[i] if i < len(defaults) else ("", "")
        sk1, sk2 = st.columns([1, 2])
        with sk1:
            st.text_input("Category", key=f"cv_scat_{i}",
                          value=dc if f"cv_scat_{i}" not in st.session_state else None,
                          placeholder="Programming Languages")
        with sk2:
            st.text_input("Skills (comma separated)", key=f"cv_sitems_{i}",
                          value=di if f"cv_sitems_{i}" not in st.session_state else None,
                          placeholder="Python, Java, C++")

    _divider()

    # ═════════════════════════════════════════════════════════════════════════
    # 6. EDUCATION
    # ═════════════════════════════════════════════════════════════════════════
    st.markdown("### 🎓 Education")

    ea, eb, _ = st.columns([1, 1, 4])
    with ea:
        if st.button("＋ Add", key="add_edu", use_container_width=True):
            st.session_state.cv_edu_count = min(st.session_state.cv_edu_count + 1, 4)
            st.rerun()
    with eb:
        if st.button("－ Remove", key="rem_edu", use_container_width=True):
            st.session_state.cv_edu_count = max(st.session_state.cv_edu_count - 1, 1)
            st.rerun()

    for i in range(st.session_state.cv_edu_count):
        with st.expander(f"Education {i+1}", expanded=True):
            ed1, ed2 = st.columns(2)
            with ed1:
                st.text_input("Degree / Program", key=f"cv_edeg_{i}",
                              placeholder="B.Tech Computer Science (AI & ML)")
                st.text_input("Institution",      key=f"cv_einst_{i}",
                              placeholder="JSS University")
                st.text_input("Location",         key=f"cv_eloc2_{i}",
                              placeholder="Noida, India")
            with ed2:
                st.text_input("Start",            key=f"cv_estart2_{i}", placeholder="Aug 2025")
                st.text_input("End / Expected",   key=f"cv_eend2_{i}",   placeholder="May 2029")
                st.text_input("GPA / CGPA / %",   key=f"cv_egpa_{i}",    placeholder="8.5 / 10")
            st.text_input("Relevant Coursework", key=f"cv_ecourses_{i}",
                          placeholder="DSA, Python, OOP, Software Engineering, ML Fundamentals")

    _divider()

    # ═════════════════════════════════════════════════════════════════════════
    # 7. CERTIFICATIONS
    # ═════════════════════════════════════════════════════════════════════════
    st.markdown("### 🏅 Certifications")
    _tip("One per line. Format: Name | Platform | Year")
    st.text_area("Certifications", height=90, key="cv_certs",
                 label_visibility="collapsed",
                 placeholder=(
                     "Machine Learning Specialization | Coursera (DeepLearning.AI) | 2025\n"
                     "Python for Data Science | IBM / Coursera | 2024"
                 ))

    _divider()

    # ═════════════════════════════════════════════════════════════════════════
    # GENERATE
    # ═════════════════════════════════════════════════════════════════════════
    name_val  = st.session_state.get("cv_name", "").strip()
    email_val = st.session_state.get("cv_email", "").strip()

    if not name_val or not email_val:
        st.warning("⚠️ Fill in at least your **Full Name** and **Email** to generate.")
    else:
        _, btn_col, _ = st.columns([1, 1, 1])
        with btn_col:
            gen = st.button("⚡ Generate Resume PDF", use_container_width=True, key="gen_cv_pdf")

        if gen:
            # ── Collect ALL data from session state directly ──────────────────
            # (avoids empty-widget problem when expanders are collapsed)
            def ss(key, fallback=""):
                return st.session_state.get(key, fallback) or fallback

            # experiences
            experiences = []
            for i in range(st.session_state.cv_exp_count):
                title = ss(f"cv_etitle_{i}")
                comp  = ss(f"cv_ecomp_{i}")
                if not title and not comp:
                    continue
                raw_b = ss(f"cv_ebullets_{i}")
                bullets = [l.strip() for l in raw_b.split('\n') if l.strip()] if raw_b else []
                experiences.append({
                    'title': title, 'company': comp,
                    'location': ss(f"cv_eloc_{i}"),
                    'start': ss(f"cv_estart_{i}"), 'end': ss(f"cv_eend_{i}"),
                    'bullets': bullets,
                })

            # projects
            projects = []
            for i in range(st.session_state.cv_proj_count):
                pname = ss(f"cv_pname_{i}")
                if not pname:
                    continue
                raw_b = ss(f"cv_pbullets_{i}")
                bullets = [l.strip() for l in raw_b.split('\n') if l.strip()] if raw_b else []
                projects.append({
                    'name': pname, 'tech': ss(f"cv_ptech_{i}"),
                    'link': ss(f"cv_plink_{i}"), 'bullets': bullets,
                })

            # skills
            skills = []
            for i in range(st.session_state.cv_skill_count):
                cat   = ss(f"cv_scat_{i}")
                items = ss(f"cv_sitems_{i}")
                if cat and items:
                    skills.append({'category': cat, 'items': items})

            # educations
            educations = []
            for i in range(st.session_state.cv_edu_count):
                deg  = ss(f"cv_edeg_{i}")
                inst = ss(f"cv_einst_{i}")
                if not deg and not inst:
                    continue
                educations.append({
                    'degree': deg, 'institution': inst,
                    'location': ss(f"cv_eloc2_{i}"),
                    'start': ss(f"cv_estart2_{i}"), 'end': ss(f"cv_eend2_{i}"),
                    'gpa': ss(f"cv_egpa_{i}"), 'courses': ss(f"cv_ecourses_{i}"),
                })

            # certifications
            certs_raw = ss("cv_certs")
            certifications = [c.strip() for c in certs_raw.split('\n') if c.strip()]

            resume_data = {
                'name':     ss("cv_name"),    'tagline':  ss("cv_tagline"),
                'email':    ss("cv_email"),   'phone':    ss("cv_phone"),
                'location': ss("cv_location"),'linkedin': ss("cv_linkedin"),
                'github':   ss("cv_github"),  'summary':  ss("cv_summary"),
                'experiences':    experiences,
                'projects':       projects,
                'skills':         skills,
                'educations':     educations,
                'certifications': certifications,
            }

            with st.spinner("Building your resume PDF..."):
                try:
                    pdf_bytes = generate_resume_pdf(resume_data)
                    st.session_state.cv_pdf_bytes = pdf_bytes
                    st.session_state.cv_pdf_name  = ss("cv_name").replace(' ', '_') + "_Resume.pdf"
                except Exception as e:
                    st.error(f"❌ PDF generation failed: {e}")
                    st.info("Make sure reportlab is installed: `pip install reportlab`")

        # ── Show download if PDF is ready ─────────────────────────────────────
        if st.session_state.cv_pdf_bytes:
            st.success("✅ Resume PDF generated!")

            _, dl_col, _ = st.columns([1, 1, 1])
            with dl_col:
                st.download_button(
                    "📥 Download Resume PDF",
                    data=st.session_state.cv_pdf_bytes,
                    file_name=st.session_state.cv_pdf_name,
                    mime="application/pdf",
                    use_container_width=True,
                )

            # checklist — read from session state directly
            def ss(k, f=""): return st.session_state.get(k, f) or f

            exp_count  = sum(1 for i in range(st.session_state.cv_exp_count)
                             if ss(f"cv_etitle_{i}") or ss(f"cv_ecomp_{i}"))
            proj_count = sum(1 for i in range(st.session_state.cv_proj_count)
                             if ss(f"cv_pname_{i}"))
            skill_count= sum(1 for i in range(st.session_state.cv_skill_count)
                             if ss(f"cv_scat_{i}") and ss(f"cv_sitems_{i}"))
            edu_count  = sum(1 for i in range(st.session_state.cv_edu_count)
                             if ss(f"cv_edeg_{i}") or ss(f"cv_einst_{i}"))
            cert_count = len([c for c in ss("cv_certs").split('\n') if c.strip()])
            has_summary= bool(ss("cv_summary"))

            st.markdown(f"""
            <div style='background:#0d1a0d;border:1px solid #1a401a;border-radius:10px;
                        padding:1rem 1.2rem;margin-top:0.5rem'>
                <div style='color:#00ff88;font-weight:700;margin-bottom:0.5rem'>📄 Resume includes:</div>
                <div style='color:#80c080;font-size:0.85rem;line-height:1.9'>
                    {'✅' if has_summary  else '⚪'} Professional Summary<br>
                    {'✅' if exp_count>0  else '⚪'} Work Experience ({exp_count} positions)<br>
                    {'✅' if proj_count>0 else '⚪'} Projects ({proj_count} projects)<br>
                    {'✅' if skill_count>0 else '⚪'} Skills ({skill_count} categories)<br>
                    {'✅' if edu_count>0  else '⚪'} Education ({edu_count} entries)<br>
                    {'✅' if cert_count>0 else '⚪'} Certifications ({cert_count} listed)
                </div>
            </div>""", unsafe_allow_html=True)

    # ── Tips ──────────────────────────────────────────────────────────────────
    _divider()
    st.markdown("""
    <div style='background:#111125;border:1px solid #1e1e40;border-radius:12px;
                padding:1.2rem 1.5rem'>
        <div style='font-weight:700;color:#c0c0ff;margin-bottom:0.8rem'>
            💡 Tips for a strong ATS resume
        </div>
        <div style='font-size:0.83rem;color:#7878a0;line-height:1.9'>
            • Use <b style='color:#c0c0ff'>exact keywords from the job description</b> in your skills and bullets<br>
            • <b style='color:#c0c0ff'>Quantify everything</b> — "98% accuracy on 635 samples" beats "high accuracy"<br>
            • Start every bullet with a <b style='color:#c0c0ff'>strong action verb</b>: Built, Achieved, Deployed, Reduced<br>
            • Keep to <b style='color:#c0c0ff'>1 page</b> as a fresher — every word counts<br>
            • After building, run it through the <b style='color:#c0c0ff'>🔍 Analyzer</b> to check your ATS score
        </div>
    </div>""", unsafe_allow_html=True)

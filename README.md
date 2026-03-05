# ⚡ AI-Powered ATS Resume Analyzer

> **AI for Bharat Hackathon 2026** — Beat the bots. Land the interview.

[![Live Demo](https://img.shields.io/badge/Live%20Demo-Streamlit-FF4B4B?style=for-the-badge&logo=streamlit)](https://resume-analyzer-ai-powered.streamlit.app/)
[![AWS Bedrock](https://img.shields.io/badge/AWS-Bedrock-FF9900?style=for-the-badge&logo=amazonaws)](https://aws.amazon.com/bedrock/)
[![Python](https://img.shields.io/badge/Python-3.10+-3776AB?style=for-the-badge&logo=python)](https://python.org)

An intelligent resume optimization tool that helps job seekers — students, freshers, and professionals — analyze their resumes against job descriptions and build better ones. Built with a hybrid architecture: custom NLP engine for core analysis, and a triple-AI fallback chain for generative features.

🔗 **[Try it live → resume-analyzer-ai-powered.streamlit.app](https://resume-analyzer-ai-powered.streamlit.app/)**

---

## ✨ Features

| Feature | Description |
|---------|-------------|
| ⚡ **ATS Score** | Hybrid TF-IDF + AI scoring (0–100), calibrated per candidate level |
| 🔍 **Keyword Gap Analysis** | Missing JD keywords ranked by importance, grouped by category |
| 📋 **Section Evaluation** | Per-section scoring with mode-aware feedback (student / intern / professional) |
| 🤖 **AI Suggestions** | Personalized, resume-specific recommendations — not generic tips |
| 🚨 **Eligibility Warnings** | Detects hard blockers: graduation requirements, experience gaps |
| ✏️ **CV Builder** | Integrated resume editor with live preview, AI rewriting per section, PDF export |
| 🔄 **Auto-fill** | One-click import from uploaded resume into CV Builder |
| 📊 **Generate Content** | AI-generated summaries, skills, experience bullets, and certifications |
| 📥 **Export** | Download full analysis report + polished resume PDF |

---

## 🏗️ Architecture

The app uses a **two-layer hybrid approach**:

**Layer 1 — Local NLP Engine (no API needed):**
- TF-IDF similarity scoring via scikit-learn
- Custom keyword extraction and gap analysis
- Section completeness evaluation
- Rule-based smart suggestions

**Layer 2 — Generative AI (triple fallback chain):**
```
Amazon Bedrock (Claude Haiku 4.5)  ← PRIMARY
        ↓ (if throttled)
Groq / Llama 3.3 70B               ← SECONDARY
        ↓ (if rate limited)
Google Gemini Flash                 ← TERTIARY
        ↓ (if all unavailable)
Smart rule-based suggestions        ← ALWAYS WORKS
```

~70% of functionality (scoring, keyword analysis, suggestions) runs fully locally with zero API dependency.

---

## 🛠️ Tech Stack

| Layer | Technology |
|-------|-----------|
| Frontend | Streamlit (multi-page) |
| NLP / Scoring | scikit-learn, TF-IDF, Cosine Similarity |
| PDF Parsing | pdfplumber + PyPDF2 fallback |
| Primary AI | Amazon Bedrock — Claude Haiku 4.5 |
| Secondary AI | Groq — Llama 3.3 70B |
| Tertiary AI | Google Gemini Flash |
| PDF Generation | ReportLab |
| Deployment | Streamlit Cloud |

---

## 📦 Setup & Installation

### 1. Clone the repository
```bash
git clone https://github.com/YOUR_USERNAME/ats-resume-analyzer.git
cd ats-resume-analyzer
```

### 2. Install dependencies
```bash
pip install -r requirements.txt
```

### 3. Configure API keys

Create a `.env` file in the root directory:

```env
# Primary AI — Amazon Bedrock (recommended)
AWS_ACCESS_KEY_ID=your_access_key
AWS_SECRET_ACCESS_KEY=your_secret_key
AWS_DEFAULT_REGION=us-east-1

# Secondary AI — Groq (free at console.groq.com)
GROQ_API_KEY=gsk_...

# Tertiary AI — Google Gemini (free at aistudio.google.com)
GEMINI_API_KEY=AIza...
```

You only need **one** key to use AI features. The app works without any key for core analysis.

### 4. Run the app
```bash
streamlit run app.py
```

### 5. Open in browser
```
http://localhost:8501
```

---

## ☁️ Deploy to Streamlit Cloud

1. Push this repo to GitHub
2. Go to [share.streamlit.io](https://share.streamlit.io) → **New app** → select repo → main file: `app.py`
3. Go to **Settings → Secrets** and add:
```toml
AWS_ACCESS_KEY_ID = "your_key"
AWS_SECRET_ACCESS_KEY = "your_secret"
AWS_DEFAULT_REGION = "us-east-1"
GROQ_API_KEY = "your_key"
GEMINI_API_KEY = "your_key"
```
4. Click **Deploy**

---

## 📁 Project Structure

```
ats-resume-analyzer/
├── app.py                        # Main app + ATS analyzer page
├── requirements.txt
├── pages/
│   └── cv_builder.py             # CV Builder — editor, preview, PDF export
├── components/
│   ├── ai_suggester.py           # Bedrock / Groq / Gemini — triple fallback
│   ├── keyword_analyzer.py       # Keyword extraction and gap analysis
│   ├── score_calculator.py       # TF-IDF ATS scoring engine
│   ├── section_evaluator.py      # Per-section resume evaluation
│   ├── resume_extractor.py       # Structured resume parsing
│   ├── cv_generator.py           # PDF resume generation
│   └── pdf_parser.py             # PDF text extraction
└── utils/
    └── text_processor.py         # Shared text preprocessing
```

---

## 🎯 How It Works

```
PDF Upload → Text Extraction → Job Description Input → Candidate Mode Selection
                                        ↓
                          TF-IDF Similarity Score
                                        ↓
                     AI-Enhanced Score Blending (60/40)
                                        ↓
                    Keyword Gap Analysis (ranked by importance)
                                        ↓
                      Section-by-Section Evaluation
                                        ↓
                    Eligibility Check (graduation / experience)
                                        ↓
                  Mode-Aware AI Suggestions (student / pro)
                                        ↓
              CV Builder — auto-fill, AI rewrite, PDF export
```

---

## 👤 Team

Built for the **AI for Bharat Hackathon 2026** — powered by AWS Bedrock.

---

## 📄 License

MIT License — free to use and modify.
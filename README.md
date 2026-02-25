# ⚡ AI-Powered ATS Resume Analyzer

> **AI for Bharat Hackathon 2025** — Beat the bots. Land the interview.

An intelligent resume analysis tool that helps students optimize their resumes for Applicant Tracking Systems (ATS). Upload your resume PDF, paste a job description, and get instant AI-powered insights.

---

## 🚀 Features

| Feature | Description |
|---------|-------------|
| ⚡ **ATS Score** | TF-IDF powered compatibility score (0–100) |
| 🔍 **Keyword Gap Analysis** | Identifies missing technical & professional keywords ranked by importance |
| 📋 **Section Evaluation** | Scores each resume section (Contact, Skills, Experience, Education, Projects) |
| 🤖 **AI Suggestions** | Google Gemini-powered personalized improvement recommendations |
| ✨ **Content Generator** | AI-generated content for missing resume sections |
| 📥 **Export** | Download full analysis report and generated content |

---

## 🛠️ Tech Stack

- **Frontend**: Streamlit (Python)
- **NLP/ML**: scikit-learn (TF-IDF, Cosine Similarity)
- **PDF Parsing**: pdfplumber + PyPDF2 (fallback)
- **AI**: Google Gemini 1.5 Flash (free tier)
- **Deployment**: Streamlit Cloud

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

### 3. Get a free Gemini API Key
- Go to [aistudio.google.com](https://aistudio.google.com)
- Sign in with Google → Get API Key → Create API Key
- Copy the key (starts with `AIza...`)

### 4. Run the app
```bash
streamlit run app.py
```

### 5. Open in browser
```
http://localhost:8501
```

---

## 🌐 Deploy to Streamlit Cloud (Free)

1. Push this repo to GitHub
2. Go to [share.streamlit.io](https://share.streamlit.io)
3. Click **New app** → Select your repo → Set main file: `app.py`
4. Click **Deploy** — done in ~2 minutes!

> **Note**: Add your Gemini API key directly in the app's sidebar — no server-side secrets needed.

---

## 📁 Project Structure

```
ats-resume-analyzer/
├── app.py                          # Main Streamlit application
├── requirements.txt                # Python dependencies
├── .streamlit/
│   └── config.toml                 # Streamlit dark theme config
├── components/
│   ├── pdf_parser.py               # PDF text extraction (pdfplumber + PyPDF2)
│   ├── score_calculator.py         # TF-IDF ATS scoring
│   ├── keyword_analyzer.py         # Keyword gap analysis
│   ├── section_evaluator.py        # Resume section scoring
│   └── ai_suggester.py             # Gemini AI suggestions & content generation
└── utils/
    └── text_processor.py           # Shared text preprocessing
```

---

## 🎯 How It Works

```
PDF Upload → Text Extraction → Job Description Input
     ↓
TF-IDF Similarity Score (ATS Score)
     ↓
Keyword Gap Analysis (Missing Terms, Ranked by Importance)
     ↓
Section-by-Section Evaluation (Contact, Skills, Experience, Education)
     ↓
AI-Powered Suggestions (Google Gemini)
     ↓
Content Generation for Missing Sections
     ↓
Downloadable Report
```

---

## 👤 Team

Built solo for the **AI for Bharat Hackathon 2025**.

---

## 📄 License

MIT License — free to use and modify.

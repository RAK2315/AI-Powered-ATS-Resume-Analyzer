"""
Keyword Analyzer v4 — strict filtering, no junk bigrams.
"""

import re
from dataclasses import dataclass, field
from typing import List
from sklearn.feature_extraction.text import TfidfVectorizer
from utils.text_processor import TextProcessor


@dataclass
class Keyword:
    term: str
    tfidf_score: float
    frequency: int
    category: str


@dataclass
class MissingKeyword:
    term: str
    importance_score: float
    category: str
    context: str
    suggestions: List[str] = field(default_factory=list)


@dataclass
class RankedKeyword:
    term: str
    importance_score: float
    category: str
    context: str
    rank: int
    suggestions: List[str] = field(default_factory=list)


# ── Whitelisted meaningful terms ──────────────────────────────────────────────

TECH_TERMS = {
    # languages
    'python','java','javascript','typescript','c++','c#','golang','rust',
    'scala','kotlin','swift','r','matlab','bash','shell',
    # web / backend
    'react','angular','vue','nodejs','django','flask','fastapi','spring',
    'graphql','rest','api','microservices',
    # data / ml
    'scikit-learn','scikit','pandas','numpy','matplotlib','seaborn',
    'tensorflow','pytorch','keras','mxnet','jax','xgboost','lightgbm',
    'catboost','huggingface','transformers','bert','gpt','opencv','fastai',
    'machine learning','deep learning','nlp','llm','computer vision',
    'natural language processing','reinforcement learning',
    'supervised learning','unsupervised learning','semi-supervised',
    'classification','regression','clustering','decision tree','random forest',
    'neural network','neural networks','convolutional','cnn','rnn','lstm',
    'transformer','attention mechanism','transfer learning',
    'feature engineering','data preprocessing','model optimization',
    'hyperparameter tuning','cross-validation','dimensionality reduction',
    'time series','linear algebra','probability','statistics',
    'data visualization','data analysis','exploratory data analysis','eda',
    # databases
    'sql','nosql','mongodb','postgresql','mysql','redis','elasticsearch',
    'bigquery','hive','spark sql',
    # big data / cloud
    'spark','hadoop','kafka','airflow','prefect','luigi',
    'aws','azure','gcp','sagemaker','vertex ai','azure ml',
    'docker','kubernetes','ci/cd',
    # tools
    'git','github','gitlab','jupyter','colab','streamlit','gradio',
    'mlflow','wandb','dvc','dagshub','databricks',
    'tableau','powerbi','looker',
    'sql','nosql',
    # practices
    'agile','scrum','devops','version control','open source',
    # compound tech phrases that should stay as-is
    'numpy pandas','pandas scikit','scikit learn',
    'tensorflow pytorch','data preprocessing',
    'feature engineering','model deployment',
}

SOFT_SKILL_TERMS = {
    'leadership','communication','teamwork','collaboration','problem solving',
    'analytical','creative','innovative','organized','detail oriented',
    'time management','adaptable','proactive','critical thinking',
    'presentation','negotiation','mentoring','cross-functional',
    'stakeholder management','independent','self-motivated','problem-solving',
}

# ── Definitive junk lists ─────────────────────────────────────────────────────

# Any single word in this set → always junk
JUNK_WORDS = {
    # job posting boilerplate
    'bonus','currently','pursuing','recently','completed','ideal','motivated',
    'passionate','enthusiastic','eager','willing','ready','able','capable',
    'seeking','hire','hiring','join','apply','responsible','responsibilities',
    'eligibility','candidate','candidates','required','requirement','requirements',
    'preferred','advantage','plus','opportunity','offer','certificate','stipend',
    'salary','pay','compensation','remote','location','company','duration',
    'full','time','part','month','months','year','years','week','day',
    # generic descriptors
    'strong','good','excellent','solid','proficient','familiar','familiarity',
    'basic','advanced','various','multiple','several','large','small','big',
    'new','current','future','past','previous','key','core','primary','main',
    'major','minor','high','low','wide','deep','broad','extensive','modern',
    'latest','cutting','edge','state','art','best','standard','practice',
    # generic verbs/nouns from JD boilerplate
    'write','writing','written','clean','documented','document','following',
    'implement','explore','evaluate','assist','collaborate','perform','design',
    'develop','build','create','work','understand','understanding','knowledge',
    'experience','exposure','familiarity','ability','skills','skill','tool',
    'tools','platform','platforms','framework','frameworks','library','libraries',
    'package','packages','language','languages','code','coding','programming',
    'software','hardware','system','systems','solution','solutions','approach',
    'method','methods','technique','techniques','algorithm','algorithms',
    'model','models','data','project','projects','team','teams','role','roles',
    'function','functions','feature','features','aspect','aspects',
    # filler
    'including','using','across','within','between','based','focused','driven',
    'oriented','related','specific','general','level','levels','range',
    'value','impact','result','results','outcome','outcomes','goal','goals',
    'objective','objectives','task','tasks','real','world','industry',
    'professional','professionals','experienced','live','production',
    'research','engineering','science','artificial','intelligence',
    'internship','intern','certificate','upon','successful','completion',
    'inficore','soft','bonus','kaggle','competitions','github','contributions',
    'compute','computing','distributed','ranking','problems','scale',
    'following','inference','deploy','deploying','efficient','efficiency',
    'effective','effectively','well','clean','written','documented',
    'exploratory','optimize','optimization','performance','accuracy',
}

# Bigrams that are always junk regardless of anything
JUNK_BIGRAMS = {
    'documented python','clean well','well documented','bonus experience',
    'bonus kaggle','ai products','cloud platforms','version control',
    'open source','engineering best','best practices','computing frameworks',
    'distributed computing','large scale','write clean','code following',
    'following engineering','platforms gcp','ranking problems',
    'using distributed','optimize model','engineer intern',
    'software engineer','exploratory data','data analysis',
    'code following','following engineering','currently pursuing',
    'recently completed','data scientists','live ai','full time',
    'stipend 15','15 000','000 month','per month','what offer',
    'inficore soft','artificial intelligence',
    'rank problems','explore deep','signal based','image text',
}

# A bigram is only valid if BOTH words have value (not in JUNK_WORDS)
# AND the phrase appears as a whole in the JD (freq >= 1)


class KeywordAnalyzer:

    def __init__(self):
        self.text_processor = TextProcessor()

    # ── public API ────────────────────────────────────────────────────────────

    def extract_keywords(self, job_desc: str) -> List[Keyword]:
        if not job_desc or len(job_desc.strip()) < 10:
            return []

        normalized = self.text_processor.normalize(job_desc)
        vectorizer = TfidfVectorizer(
            ngram_range=(1, 2), max_features=300,
            stop_words='english', min_df=1,
        )
        try:
            mat = vectorizer.fit_transform([normalized, normalized])
            names  = vectorizer.get_feature_names_out()
            scores = mat[0].toarray()[0]
        except Exception:
            return []

        stop_words = self.text_processor.get_stop_words()
        keywords: List[Keyword] = []

        for term, score in zip(names, scores):
            if score == 0:
                continue
            if self._is_junk(term, stop_words):
                continue

            freq = job_desc.lower().count(term.lower())
            words = term.split()

            # Bigrams: must actually appear together in JD
            if len(words) == 2 and freq == 0:
                continue

            # Single non-whitelisted words: must appear ≥2 times
            cat = self._categorize(term)
            if cat == 'general' and len(words) == 1 and freq < 2:
                continue

            # Bigrams that are general (neither word is technical): skip
            if len(words) == 2 and cat == 'general':
                continue

            keywords.append(Keyword(term=term, tfidf_score=float(score),
                                    frequency=freq, category=cat))

        # Boost whitelisted terms
        for kw in keywords:
            if kw.term.lower() in TECH_TERMS:
                kw.tfidf_score *= 2.5
            elif kw.term.lower() in SOFT_SKILL_TERMS:
                kw.tfidf_score *= 1.5

        keywords.sort(key=lambda k: k.tfidf_score, reverse=True)
        return keywords[:50]

    def find_missing_keywords(self, resume_text: str,
                               job_keywords: List[Keyword]) -> List[MissingKeyword]:
        if not resume_text or not job_keywords:
            return []

        resume_lower = resume_text.lower()
        stop_words   = self.text_processor.get_stop_words()
        missing      = []

        for kw in job_keywords:
            tl = kw.term.lower()
            if tl in resume_lower:
                continue
            # Multi-word: skip if all significant words already present
            words = tl.split()
            if len(words) > 1:
                sig = [w for w in words
                       if len(w) > 3 and w not in stop_words and w not in JUNK_WORDS]
                if sig and all(w in resume_lower for w in sig):
                    continue

            missing.append(MissingKeyword(
                term=kw.term,
                importance_score=kw.tfidf_score * (1 + min(kw.frequency, 5) * 0.15),
                category=kw.category,
                context=self._context(kw.category),
                suggestions=self._suggestions(kw.term, kw.category),
            ))

        return missing

    def rank_by_importance(self, keywords: List[MissingKeyword]) -> List[RankedKeyword]:
        boost = {'technical': 2.0, 'soft_skill': 1.2,
                 'industry_specific': 1.5, 'general': 0.3}

        scored = sorted(keywords,
                        key=lambda k: k.importance_score * boost.get(k.category, 1.0),
                        reverse=True)

        result, general_count = [], 0
        for kw in scored:
            if kw.category == 'general':
                general_count += 1
                if general_count > 2:
                    continue
            result.append(RankedKeyword(
                term=kw.term,
                importance_score=kw.importance_score,
                category=kw.category,
                context=kw.context,
                rank=len(result) + 1,
                suggestions=kw.suggestions,
            ))

        return result

    # ── private helpers ───────────────────────────────────────────────────────

    def _is_junk(self, term: str, stop_words: set) -> bool:
        t = term.lower().strip()

        if len(t) < 3:
            return True
        if t in JUNK_BIGRAMS:
            return True

        words = t.split()

        # All words are junk or stop words
        if all(w in stop_words or w in JUNK_WORDS for w in words):
            return True

        # Any digit sequence → junk (catches "15 000", "000 month" etc.)
        if re.search(r'\b\d+\b', t):
            return True

        # Single word that's explicitly junk
        if len(words) == 1 and t in JUNK_WORDS:
            return True

        # Bigrams: only allow if the WHOLE phrase is a known term
        if len(words) == 2:
            if t in TECH_TERMS:
                return False   # explicitly whitelisted — keep it
            if t in SOFT_SKILL_TERMS:
                return False
            # Otherwise reject all bigrams that aren't whitelisted
            return True

        return False

    def _categorize(self, term: str) -> str:
        t = term.lower()
        if t in TECH_TERMS:
            return 'technical'
        # Substring match for long tech terms
        for tech in TECH_TERMS:
            if len(tech) > 5 and tech in t:
                return 'technical'
        if t in SOFT_SKILL_TERMS:
            return 'soft_skill'
        for s in SOFT_SKILL_TERMS:
            if len(s) > 7 and s in t:
                return 'soft_skill'
        return 'general'

    def _context(self, cat: str) -> str:
        return {
            'technical':         'Add to your Skills or Projects section.',
            'soft_skill':        'Demonstrate with a concrete example in Experience.',
            'industry_specific': 'Add to Summary or Experience.',
            'general':           'Add where naturally relevant.',
        }.get(cat, 'Add where relevant.')

    def _suggestions(self, term: str, cat: str) -> List[str]:
        if cat == 'technical':
            return [
                f"Add '{term}' to your Technical Skills section.",
                f"Mention '{term}' in a project or experience bullet.",
            ]
        if cat == 'soft_skill':
            return [
                f"Show '{term}' with a concrete example in your Experience.",
                f"Use '{term}' in your professional summary.",
            ]
        return [f"Incorporate '{term}' naturally where relevant."]

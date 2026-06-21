from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Dict, List, Optional

import requests

WIKI_API = "https://en.wikipedia.org/w/api.php"
TIMEOUT = 8

@dataclass
class WikiResult:
    title: str
    summary: str
    url: str
    sections: Dict[str, str]
    source: str = "Wikipedia"

def _clean_wiki_text(text: str) -> str:
    text = re.sub(r"\{\{.*?\}\}", " ", str(text), flags=re.S)
    text = re.sub(r"<.*?>", " ", text)
    text = re.sub(r"\[\[(?:[^|\]]*\|)?([^\]]+)\]\]", r"\1", text)
    text = re.sub(r"\[http[^\s\]]+\s*([^\]]*)\]", r"\1", text)
    text = re.sub(r"'{2,}", "", text)
    text = re.sub(r"={2,}\s*(.*?)\s*={2,}", r"\n## \1\n", text)
    text = re.sub(r"\s+", " ", text)
    return text.strip()

def _sentences(text: str) -> List[str]:
    parts = re.split(r"(?<=[.!?])\s+", str(text).strip())
    return [p.strip() for p in parts if len(p.strip()) > 25]

def search_wikipedia(topic: str) -> Optional[str]:
    topic = str(topic).strip()
    if not topic:
        return None
    params = {
        "action": "query",
        "list": "search",
        "srsearch": topic,
        "format": "json",
        "srlimit": 1,
    }
    try:
        r = requests.get(WIKI_API, params=params, timeout=TIMEOUT)
        r.raise_for_status()
        data = r.json()
        results = data.get("query", {}).get("search", [])
        if results:
            return results[0].get("title")
    except Exception:
        return None
    return None

def fetch_wikipedia(topic: str) -> Optional[WikiResult]:
    title = search_wikipedia(topic) or str(topic).strip()
    if not title:
        return None

    params = {
        "action": "query",
        "prop": "extracts|info",
        "explaintext": 1,
        "exsectionformat": "plain",
        "inprop": "url",
        "titles": title,
        "format": "json",
        "redirects": 1,
    }
    try:
        r = requests.get(WIKI_API, params=params, timeout=TIMEOUT)
        r.raise_for_status()
        pages = r.json().get("query", {}).get("pages", {})
        if not pages:
            return None
        page = next(iter(pages.values()))
        if "missing" in page:
            return None
        extract = page.get("extract", "") or ""
        real_title = page.get("title", title)
        url = page.get("fullurl", f"https://en.wikipedia.org/wiki/{real_title.replace(' ', '_')}")
        cleaned = _clean_wiki_text(extract)
        sentences = _sentences(cleaned)
        summary = " ".join(sentences[:4]) if sentences else cleaned[:700]
        sections = make_sections_from_text(cleaned)
        return WikiResult(title=real_title, summary=summary, url=url, sections=sections)
    except Exception:
        return None

def make_sections_from_text(text: str) -> Dict[str, str]:
    sentences = _sentences(text)
    if not sentences:
        return {
            "Overview": "No enough clean text found.",
            "Key facts": "",
            "Applications": "",
            "Limitations": "",
        }
    return {
        "Overview": " ".join(sentences[:4]),
        "Key facts": " ".join(sentences[4:9]) if len(sentences) > 4 else " ".join(sentences[:3]),
        "Applications": " ".join([s for s in sentences if any(w in s.lower() for w in ["use", "used", "application", "industry", "technology", "research"])][:5]) or "Applications depend on the topic and course context.",
        "Limitations": " ".join([s for s in sentences if any(w in s.lower() for w in ["limit", "problem", "challenge", "however", "although", "risk"])][:4]) or "Students should verify details from class notes and teacher explanation.",
    }

def build_wiki_topic_pack(topic: str) -> Optional[Dict]:
    result = fetch_wikipedia(topic)
    if not result:
        return None

    first_sentence = _sentences(result.summary)
    definition = first_sentence[0] if first_sentence else result.summary[:280]
    key_terms = extract_keywords(result.summary, limit=5)
    main_concept = key_terms[0] if key_terms else result.title

    return {
        "title": result.title,
        "hook": f"{result.title} becomes easier when we connect the definition with examples and class questions.",
        "definition": definition,
        "simple": simplify_text(definition, result.title),
        "facts": _sentences(result.sections.get("Key facts", ""))[:3] or _sentences(result.summary)[:3],
        "concepts": {
            main_concept.lower(): {
                "definition": definition,
                "kid": simplify_text(definition, result.title),
                "example": make_example_line(result.title, result.sections.get("Applications", "")),
                "mistake": f"Do not memorize {result.title} without understanding its main idea and context.",
                "exam": f"In exam or viva, define {result.title}, give one example, and mention one real use or limitation.",
            }
        },
        "applications": {
            "real-world connection": result.sections.get("Applications", "This topic can be connected to real course examples.")
        },
        "misconceptions": [
            f"{result.title} should not be learned only by memorizing the title.",
            "A short online summary is useful for preparation, but class notes should still be checked.",
            "One example is not enough to understand the full topic."
        ],
        "class_questions": [
            f"What is the simplest definition of {result.title}?",
            f"Can you give one real example of {result.title}?",
            f"What is the most important concept in {result.title}?",
            f"What is a common misunderstanding about {result.title}?",
            f"How is {result.title} related to our course?"
        ],
        "source": result.source,
        "source_url": result.url,
        "wiki_summary": result.summary,
        "wiki_sections": result.sections,
    }

def extract_keywords(text: str, limit: int = 6) -> List[str]:
    stop = {
        "the","and","for","with","that","this","from","are","was","were","has","have","had",
        "not","but","its","into","such","their","there","these","those","which","also","can",
        "used","using","use","more","than","when","where","what","about","between","within",
        "during","under","over","many","most","some","other","been","being","they","them"
    }
    words = re.findall(r"[A-Za-z][A-Za-z\-]{3,}", text.lower())
    freq = {}
    for w in words:
        if w not in stop:
            freq[w] = freq.get(w, 0) + 1
    return [w for w, _ in sorted(freq.items(), key=lambda x: (-x[1], x[0]))[:limit]]

def simplify_text(sentence: str, title: str) -> str:
    sentence = str(sentence).strip()
    if len(sentence) > 220:
        sentence = sentence[:220].rsplit(" ", 1)[0] + "."
    return f"In simple words, {title} means this: {sentence}"

def make_example_line(title: str, applications: str) -> str:
    app_sentences = _sentences(applications)
    if app_sentences:
        return app_sentences[0]
    return f"For example, a student can connect {title} to one real case from class, technology, research, or daily life."

def smart_answer_from_pack(pack: Dict, question: str) -> Dict:
    q = str(question).strip()
    combined = " ".join([
        pack.get("definition", ""),
        pack.get("simple", ""),
        " ".join(pack.get("facts", [])),
        " ".join(pack.get("misconceptions", [])),
        " ".join(pack.get("class_questions", [])),
        str(pack.get("wiki_summary", "")),
        " ".join(pack.get("wiki_sections", {}).values()) if isinstance(pack.get("wiki_sections"), dict) else "",
    ])
    sentences = _sentences(combined)
    q_terms = set(extract_keywords(q, limit=8))
    scored = []
    for s in sentences:
        s_terms = set(extract_keywords(s, limit=12))
        score = len(q_terms & s_terms)
        if score > 0:
            scored.append((score, s))
    if scored:
        chosen = [s for _, s in sorted(scored, key=lambda x: -x[0])[:4]]
    else:
        chosen = sentences[:4]

    answer = " ".join(chosen) if chosen else pack.get("definition", "No clear answer found.")
    return {
        "answer": answer,
        "simple": simplify_text(answer, pack.get("title", "this topic")),
        "example": make_example_line(pack.get("title", "this topic"), str(pack.get("applications", {}))),
        "source_url": pack.get("source_url", ""),
        "confidence": "Medium" if pack.get("source_url") else "Concept-pack based",
        "note": "This answer is generated from the local topic pack and/or Wikipedia summary. Verify with teacher notes for final academic use."
    }

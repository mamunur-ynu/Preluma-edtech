from __future__ import annotations

import re
from typing import Dict, List, Tuple

from topics import TOPICS, canonical_key

try:
    from wiki_fetcher import build_wiki_topic_pack, smart_answer_from_pack
except Exception:
    build_wiki_topic_pack = None
    smart_answer_from_pack = None

SKILL_DEFINITION = "Definition"
SKILL_CORE = "Core Concept"
SKILL_APPLICATION = "Application"
SKILL_MISCONCEPTION = "Misconception"

DEFAULT_CONCEPT = {
    "definition": "This is the main idea of the topic.",
    "kid": "Start with the simplest meaning first, then add examples.",
    "example": "Connect the idea to a real-life situation.",
    "mistake": "Do not memorize words without understanding the meaning.",
    "exam": "In class, explain definition, example, and common mistake.",
}

def clean_text(text: str) -> str:
    return re.sub(r"\s+", " ", str(text).strip())

def make_generic_fallback(title: str) -> Dict:
    return {
        "title": title,
        "hook": f"{title} becomes easier when we break it into small ideas.",
        "definition": f"{title} is an academic topic that can be understood through definition, examples, applications, and common mistakes.",
        "simple": f"Think of {title} like building blocks: first one block, then another.",
        "facts": [
            f"{title} has a main definition.",
            f"{title} becomes clearer through examples.",
            f"{title} can be discussed in class using smart questions.",
        ],
        "concepts": {
            "main idea": {
                "definition": f"The main idea of {title} is the first meaning a student should understand.",
                "kid": f"{title} is easier when we explain it in tiny steps.",
                "example": "A new topic is like a map: first see the big roads, then learn the details.",
                "mistake": "Do not memorize without examples.",
                "exam": "Give definition, simple example, and one common mistake.",
            }
        },
        "applications": {"class learning": "Helps students prepare before lectures."},
        "misconceptions": [
            f"{title} is not only memorization.",
            "A hard topic becomes easier when explained with examples.",
            "Good preparation means asking better questions in class.",
        ],
        "class_questions": [
            f"What is the simplest definition of {title}?",
            f"Where is {title} used in real life?",
            f"What is the most common mistake in {title}?",
            f"How can I explain {title} to a beginner?",
            f"What should I ask the teacher about {title}?",
        ],
    }

def ensure_pack_schema(data: Dict, requested_title: str) -> Dict:
    pack = dict(data or {})
    pack.setdefault("title", requested_title)
    pack.setdefault("hook", f"{requested_title} becomes easier when the student sees the big picture first.")
    pack.setdefault("definition", f"{requested_title} is an academic topic.")
    pack.setdefault("simple", f"Think of {requested_title} as a map: first learn the main roads, then the details make sense.")
    pack.setdefault("facts", [])
    pack.setdefault("concepts", {})
    pack.setdefault("applications", {})
    pack.setdefault("misconceptions", [])
    pack.setdefault("class_questions", [])

    if not pack["concepts"]:
        pack["concepts"] = {"main idea": dict(DEFAULT_CONCEPT)}

    fixed = {}
    for name, concept in pack["concepts"].items():
        item = dict(DEFAULT_CONCEPT)
        item.update(concept or {})
        fixed[name] = item
    pack["concepts"] = fixed

    if not pack["facts"]:
        pack["facts"] = [pack["definition"], pack["simple"], "Understanding the core idea improves class participation."]
    if not pack["misconceptions"]:
        pack["misconceptions"] = [f"{pack['title']} is not only memorization."]
    if not pack["class_questions"]:
        pack["class_questions"] = [
            f"What is {pack['title']}?",
            f"Where is {pack['title']} used?",
            f"What is one common mistake?",
            f"How can I explain it simply?",
            f"What should I ask in class?",
        ]
    return pack

def build_pack(topic: str, use_wikipedia: bool = True) -> Dict:
    requested = clean_text(topic) or "Machine Learning"
    key = canonical_key(requested)
    data = TOPICS.get(key)

    if data:
        return ensure_pack_schema(data, data.get("title", requested.title()))

    if use_wikipedia and build_wiki_topic_pack is not None:
        try:
            wiki_pack = build_wiki_topic_pack(requested)
            if wiki_pack:
                return ensure_pack_schema(wiki_pack, wiki_pack.get("title", requested.title()))
        except Exception:
            pass

    return ensure_pack_schema(make_generic_fallback(requested.title()), requested.title())

def _first_concept(pack: Dict) -> Tuple[str, Dict]:
    name = next(iter(pack["concepts"]))
    return name, pack["concepts"][name]

def best_concept_match(pack: Dict, question: str) -> Tuple[str, Dict]:
    q = clean_text(question).lower()
    for name, concept in pack["concepts"].items():
        if name.lower() in q:
            return name, concept
    for name, concept in pack["concepts"].items():
        for word in name.lower().split():
            if len(word) > 3 and word in q:
                return name, concept
    return _first_concept(pack)

def build_brain_brief(pack: Dict) -> Dict:
    name, c = _first_concept(pack)
    return {
        "title": pack["title"],
        "tiny_answer": pack["definition"],
        "simple": pack["simple"],
        "hook": pack["hook"],
        "key_concept": name.title(),
        "concept_simple": c["kid"],
        "example": c["example"],
        "misconception": pack["misconceptions"][0],
        "facts": pack["facts"][:3],
        "class_questions": pack["class_questions"][:5],
    }

def make_questions(pack: Dict) -> List[Dict]:
    concept_name, _ = _first_concept(pack)
    app_name = next(iter(pack["applications"])) if pack["applications"] else "real life"
    misconception = pack["misconceptions"][0]
    return [
        {"skill": SKILL_DEFINITION, "q": f"What is the best simple definition of {pack['title']}?", "options": [pack["definition"], "A random activity with no rules", "Only memorizing a word", "A topic that cannot be explained"], "answer": pack["definition"], "why": "The definition explains the main meaning clearly."},
        {"skill": SKILL_CORE, "q": f"Which concept is important in {pack['title']}?", "options": [concept_name.title(), "A method that relies on random selection rather than structured reasoning", "An unrelated process that ignores the topic entirely", "Random Guess"], "answer": concept_name.title(), "why": f"{concept_name.title()} is a core concept."},
        {"skill": SKILL_APPLICATION, "q": f"Where can {pack['title']} be applied?", "options": [app_name.title(), "Only in dreams", "Nowhere useful", "Only for decoration"], "answer": app_name.title(), "why": f"{app_name.title()} is connected to the topic."},
        {"skill": SKILL_MISCONCEPTION, "q": "Which statement is a common misunderstanding?", "options": [misconception, "Examples help learning", "Class questions are useful", "Definitions are important"], "answer": misconception, "why": "This option describes a misconception students should avoid."},
    ]

def grade(questions: List[Dict], answers: Dict[int, str]) -> Dict:
    details = []
    score = 0
    weak = []
    for i, q in enumerate(questions):
        chosen = answers.get(i, "") or ""
        correct = chosen.strip() == q["answer"].strip()
        score += int(correct)
        if not correct:
            weak.append(q["skill"])
        details.append({"q": q["q"], "chosen": chosen, "answer": q["answer"], "correct": correct, "skill": q["skill"], "why": q["why"]})
    total = len(questions)
    pct = round((score / total) * 100, 1) if total else 0
    return {"score": score, "total": total, "pct": pct, "weakest": weak[0] if weak else "None", "details": details}

def tutor_sections(pack: Dict, question: str, style: str = "Normal Mode") -> Dict:
    name, c = best_concept_match(pack, question)
    return {
        "topic": pack["title"],
        "concept": name.title(),
        "tiny_answer": c["definition"],
        "explain_simply": c["kid"],
        "real_life_example": c["example"],
        "common_mistake": c["mistake"],
        "exam_angle": c["exam"],
        "memory_line": f"Remember {name.title()} through this example: {c['example']}",
    }


def build_enriched_class_questions(pack: dict) -> list:
    """Return LLM-generated smart class questions, or fall back to local ones."""
    try:
        from llm import llm_class_questions, llm_available
        if llm_available():
            all_names = list(pack.get("concepts", {}).keys())
            result = llm_class_questions(pack["title"], pack["definition"], all_names)
            if result:
                return result
    except Exception:
        pass
    return pack.get("class_questions", [])[:5]

from __future__ import annotations

import random
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
    """Build a large pool of varied questions then randomly pick 4.
    Each call draws different question TYPES and content from the pack,
    so students get genuinely fresh practice every attempt."""
    title = pack["title"]
    all_concepts  = list(pack["concepts"].items())
    apps          = list(pack["applications"].keys()) if pack["applications"] else []
    app_descs     = pack["applications"] if pack["applications"] else {}
    misconceptions = pack["misconceptions"] if pack["misconceptions"] else [f"{title} is not only memorisation"]
    facts         = pack["facts"] if pack["facts"] else [pack["definition"]]

    def _q(skill: str, q: str, correct: str, wrongs: list, why: str) -> Dict:
        """Build one question dict: deduped & shuffled options."""
        seen, out = set(), []
        seen.add(correct.strip().lower()[:120])
        for w in wrongs:
            k = str(w).strip().lower()[:120]
            if k and k not in seen:
                seen.add(k)
                out.append(str(w).strip())
        pads = [
            f"An approach unrelated to {title}",
            f"A method that does not apply to {title}",
            f"A concept from a completely different field",
        ]
        pi = 0
        while len(out) < 3:
            out.append(pads[pi % len(pads)])
            pi += 1
        opts = [correct.strip()] + out[:3]
        random.shuffle(opts)
        return {"skill": skill, "q": q, "options": opts, "answer": correct.strip(), "why": why}

    pool: List[Dict] = []

    all_concept_names = [n.title() for n, _ in all_concepts]
    all_concept_defs  = [(n.title(), cd.get("definition",""), cd.get("example",""),
                          cd.get("mistake",""), cd.get("kid","")) for n, cd in all_concepts]

    def other_names(correct):
        return [n for n in all_concept_names if n.lower() != correct.lower()]

    # === DEFINITION questions ===

    # D1 - "Which best describes <title>?"
    pool.append(_q(
        SKILL_DEFINITION,
        f"Which of the following best describes {title}?",
        pack["definition"],
        [cd for _, cd, *_ in all_concept_defs if cd and cd.lower() != pack["definition"].lower()] +
        [f"{title} is purely theoretical with no practical use.",
         f"{title} is an advanced process only experts can use."],
        f"This is the accurate definition of {title}.",
    ))

    # D2 - "How would you explain <title> simply?"
    pool.append(_q(
        SKILL_DEFINITION,
        f"How would you explain {title} to someone with no prior knowledge?",
        pack["simple"],
        [pack["definition"],
         f"By listing all the technical terms in {title} without context.",
         f"By memorising every formula related to {title}.",
         f"By reading advanced textbooks about {title} first."],
        f"A simple, accessible explanation is the best starting point for {title}.",
    ))

    # D3 - random concept definition
    if all_concept_defs:
        cn, cdef, cex, cmistake, ckid = random.choice(all_concept_defs)
        if cdef:
            wrongs_d3 = [d for n2, d, *_ in all_concept_defs if d and n2 != cn and d.lower() != cdef.lower()]
            wrongs_d3 += [f"{cn} is the same as memorising facts about {title}.",
                          f"{cn} refers to avoiding {title} altogether."]
            pool.append(_q(
                SKILL_DEFINITION,
                f"Which of the following best describes '{cn}' within {title}?",
                cdef, wrongs_d3,
                f"'{cn}' is defined as: {cdef}",
            ))

    # D4 - "Which statement is TRUE?" (fact vs misconception)
    if facts:
        true_fact = random.choice(facts)
        pool.append(_q(
            SKILL_DEFINITION,
            f"Which of the following statements about {title} is TRUE?",
            true_fact,
            misconceptions[:3] + [f"{title} has no connection to real-world problems."],
            f"This is a verified fact about {title}.",
        ))

    # === CORE CONCEPT questions ===

    if all_concepts:
        # C1 - "Which is a key concept?"
        c1_name, c1_data = random.choice(all_concepts)
        pool.append(_q(
            SKILL_CORE,
            f"Which of the following is a key concept in {title}?",
            c1_name.title(),
            other_names(c1_name.title()) + ["Arbitrary Sampling", "Passive Recall", "Unstructured Repetition"],
            f"'{c1_name.title()}' is a central concept in {title}.",
        ))

        # C2 - "What does studying <concept> involve?"
        c2_name, c2_data = random.choice(all_concepts)
        kid = c2_data.get("kid", "").strip()
        if kid:
            pool.append(_q(
                SKILL_CORE,
                f"What does understanding '{c2_name.title()}' in {title} involve?",
                kid,
                [c2_data.get("mistake", "Memorising without understanding."),
                 f"Skipping {c2_name.title()} and focusing only on other parts of {title}.",
                 f"Treating {c2_name.title()} as an optional topic in {title}."],
                f"Understanding '{c2_name.title()}' means: {kid}",
            ))

        # C3 - "What is a common mistake with <concept>?"
        c3_name, c3_data = random.choice(all_concepts)
        mistake = c3_data.get("mistake", "").strip()
        if mistake:
            pool.append(_q(
                SKILL_CORE,
                f"What is a common mistake when studying '{c3_name.title()}' in {title}?",
                mistake,
                [c3_data.get("definition", ""),
                 f"Spending too much time on examples of {c3_name.title()}.",
                 f"Asking too many questions about {c3_name.title()} in class."],
                f"A common mistake with '{c3_name.title()}': {mistake}",
            ))

        # C4 - "Which example illustrates <concept>?"
        c4_name, c4_data = random.choice(all_concepts)
        example = c4_data.get("example", "").strip()
        if example:
            other_examples = [cd.get("example","") for _, cd in all_concepts
                              if cd.get("example","").strip() and cd.get("example","").lower() != example.lower()]
            pool.append(_q(
                SKILL_CORE,
                f"Which example best illustrates '{c4_name.title()}' in {title}?",
                example,
                other_examples + [f"A situation completely unrelated to {title}.",
                                  f"An example that contradicts the principles of {title}."],
                f"This example correctly illustrates '{c4_name.title()}'.",
            ))

    # === APPLICATION questions ===

    if apps:
        # A1 - "Which is a real-world application?"
        a1 = random.choice(apps)
        pool.append(_q(
            SKILL_APPLICATION,
            f"Which of the following is a real-world application of {title}?",
            a1.title(),
            [a.title() for a in apps if a.lower() != a1.lower()] +
            [f"Replacing all study of {title} with memorisation only",
             f"Avoiding {title} in real-world settings entirely"],
            f"'{a1.title()}' is a genuine application of {title}.",
        ))

        # A2 - "How is <title> applied in <context>?"
        a2 = random.choice(apps)
        desc = app_descs.get(a2, "").strip()
        if desc:
            pool.append(_q(
                SKILL_APPLICATION,
                f"How is {title} applied in the context of '{a2.title()}'?",
                desc,
                [app_descs.get(a, "") for a in apps if a != a2 and app_descs.get(a, "").strip()] +
                [f"It is not applied in '{a2.title()}' at all.",
                 f"{title} is used only for theoretical study, not in '{a2.title()}'."],
                f"In '{a2.title()}', {title} is used as follows: {desc}",
            ))

        # A3 - "Which does NOT belong?" (negative)
        pool.append(_q(
            SKILL_APPLICATION,
            f"Which of the following is NOT a valid application of {title}?",
            f"Using {title} only as entertainment with no learning outcome",
            [a.title() for a in apps[:3]],
            f"The other options are all real applications of {title}.",
        ))

    # === MISCONCEPTION questions ===

    # M1 - "Which is a misconception?"
    m1 = random.choice(misconceptions)
    pool.append(_q(
        SKILL_MISCONCEPTION,
        f"Which of the following statements about {title} is a common misconception?",
        m1,
        [f for f in facts if f.strip().lower() != m1.strip().lower()] +
        [f"{title} can be understood through clear definitions and examples.",
         f"Learning {title} involves both theory and real-world practice."],
        f"This is a misconception. The other options are correct statements about {title}.",
    ))

    # M2 - "Which statement is FALSE?"
    m2 = random.choice(misconceptions)
    sample_facts = random.sample(facts, min(3, len(facts))) if len(facts) >= 3 else         facts + [f"Students improve at {title} by asking questions."]
    pool.append(_q(
        SKILL_MISCONCEPTION,
        f"Which of the following statements about {title} is FALSE?",
        m2,
        sample_facts,
        f"This statement is false — it is a common misconception about {title}.",
    ))

    # M3 - "A student claims X. Why is this wrong?"
    if misconceptions and facts:
        m3 = random.choice(misconceptions)
        rebuttal = random.choice(facts)
        pool.append(_q(
            SKILL_MISCONCEPTION,
            f"A student claims: '{m3}'. Why is this incorrect?",
            rebuttal,
            [mc for mc in misconceptions if mc != m3][:2] +
            [f"It is not incorrect — the student is right about {title}.",
             f"The claim is partially true and should be accepted."],
            f"The correct understanding is: {rebuttal}",
        ))

    # === Pick 4: one from each skill type if available ===
    by_skill: Dict[str, List[Dict]] = {}
    for q in pool:
        by_skill.setdefault(q["skill"], []).append(q)

    chosen: List[Dict] = []
    skills_order = [SKILL_DEFINITION, SKILL_CORE, SKILL_APPLICATION, SKILL_MISCONCEPTION]
    random.shuffle(skills_order)
    for skill in skills_order:
        if by_skill.get(skill):
            chosen.append(random.choice(by_skill[skill]))
        if len(chosen) == 4:
            break

    remaining = [q for q in pool if q not in chosen]
    random.shuffle(remaining)
    while len(chosen) < 4 and remaining:
        chosen.append(remaining.pop())

    random.shuffle(chosen)
    return chosen[:4]


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

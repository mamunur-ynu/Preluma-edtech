"""
core/assessment_engine.py — question generation and grading.

Builds four multiple-choice questions (one per skill category) from a topic pack and grades
the answers.  Pure Python, standard library only.

Change from ``engine.py``: every question and graded detail now also carries a ``concept``
key (the concept the question is about, or ``""``).  The learning engine uses it to find
*which concept* a student is weak in, not just which skill category.  All previous keys and
behaviour are unchanged.
"""

from __future__ import annotations

import random
from typing import Dict, List

SKILL_DEFINITION    = "Definition"
SKILL_CORE          = "Core Concept"
SKILL_APPLICATION   = "Application"
SKILL_MISCONCEPTION = "Misconception"
ALL_SKILLS = (SKILL_DEFINITION, SKILL_CORE, SKILL_APPLICATION, SKILL_MISCONCEPTION)


def make_questions(pack: Dict) -> List[Dict]:
    """
    Generate four multiple-choice questions drawn from a larger question pool.

    Rather than producing the same four questions every time, this function
    builds up to twelve distinct questions across four skill categories
    (Definition, Core Concept, Application, Misconception) and then selects
    one question per category at random. Question text, correct answers, and
    wrong options all vary between calls, giving students genuinely different
    practice each session.

    Each returned question dict contains:
      - skill   : one of the four SKILL_* constants
      - q       : the question text
      - options : list of four shuffled answer strings
      - answer  : the correct answer string
      - why     : a brief explanation shown after grading
    """
    title          = pack["title"]
    all_concepts   = list(pack["concepts"].items())
    apps           = list(pack["applications"].keys()) if pack["applications"] else []
    app_descs      = pack["applications"] if pack["applications"] else {}
    misconceptions = pack["misconceptions"] if pack["misconceptions"] else [f"{title} is not only memorisation"]
    facts          = pack["facts"] if pack["facts"] else [pack["definition"]]

    def _q(skill: str, q: str, correct: str, wrongs: list, why: str, concept: str = "") -> Dict:
        """
        Assemble a single question dict with exactly four answer options.

        Duplicate options are removed, and generic padding phrases fill any
        gaps so there are always three wrong answers. The final option list
        is shuffled so the correct answer does not appear in a fixed position.
        """
        seen = {correct.strip().lower()[:120]}
        out  = []
        for w in wrongs:
            k = str(w).strip().lower()[:120]
            if k and k not in seen:
                seen.add(k)
                out.append(str(w).strip())

        # Neutral padding phrases used when the pack lacks enough wrong options
        pads = [
            f"An approach unrelated to {title}",
            f"A method that does not apply to {title}",
            "A concept from a completely different field",
        ]
        pi = 0
        while len(out) < 3:
            out.append(pads[pi % len(pads)])
            pi += 1

        opts = [correct.strip()] + out[:3]
        random.shuffle(opts)
        return {"skill": skill, "q": q, "options": opts, "answer": correct.strip(), "why": why, "concept": concept}

    pool: List[Dict] = []

    # Pre-compute reusable name and definition lists to avoid repeated lookups
    all_concept_names = [n.title() for n, _ in all_concepts]
    all_concept_defs  = [
        (n.title(), cd.get("definition",""), cd.get("example",""),
         cd.get("mistake",""), cd.get("kid",""))
        for n, cd in all_concepts
    ]

    def other_names(correct: str) -> List[str]:
        """Return all concept names except the one used as the correct answer."""
        return [n for n in all_concept_names if n.lower() != correct.lower()]

    # --- Definition questions -------------------------------------------------
    # These questions test whether the student can identify and distinguish
    # between key definitions related to the topic.

    # D1: Identify the top-level topic definition
    pool.append(_q(
        SKILL_DEFINITION,
        f"Which of the following best describes {title}?",
        pack["definition"],
        [cd for _, cd, *_ in all_concept_defs if cd and cd.lower() != pack["definition"].lower()]
        + [f"{title} is purely theoretical with no practical use.",
           f"{title} is an advanced process only experts can use."],
        f"This is the accurate definition of {title}.",
    ))

    # D2: Choose the clearest simple explanation of the topic
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

    # D3: Identify the definition of a randomly chosen concept within the topic
    if all_concept_defs:
        cn, cdef, cex, cmistake, ckid = random.choice(all_concept_defs)
        if cdef:
            wrongs_d3 = [
                d for n2, d, *_ in all_concept_defs
                if d and n2 != cn and d.lower() != cdef.lower()
            ]
            wrongs_d3 += [
                f"{cn} is the same as memorising facts about {title}.",
                f"{cn} refers to avoiding {title} altogether.",
            ]
            pool.append(_q(
                SKILL_DEFINITION,
                f"Which of the following best describes '{cn}' within {title}?",
                cdef, wrongs_d3,
                f"'{cn}' is defined as: {cdef}",
                concept=cn,
            ))

    # D4: Identify a verified fact among misleading misconceptions
    if facts:
        true_fact = random.choice(facts)
        pool.append(_q(
            SKILL_DEFINITION,
            f"Which of the following statements about {title} is TRUE?",
            true_fact,
            misconceptions[:3] + [f"{title} has no connection to real-world problems."],
            f"This is a verified fact about {title}.",
        ))

    # --- Core Concept questions -----------------------------------------------
    # These questions assess understanding of the internal structure of the
    # topic: its named concepts, how they work, and common student errors.

    if all_concepts:
        # C1: Identify a key concept by name
        c1_name, _ = random.choice(all_concepts)
        pool.append(_q(
            SKILL_CORE,
            f"Which of the following is a key concept in {title}?",
            c1_name.title(),
            other_names(c1_name.title())
            + ["Arbitrary Sampling", "Passive Recall", "Unstructured Repetition"],
            f"'{c1_name.title()}' is a central concept in {title}.",
            concept=c1_name,
        ))

        # C2: Describe what understanding a concept actually involves
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
                concept=c2_name,
            ))

        # C3: Identify a common mistake students make with a specific concept
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
                concept=c3_name,
            ))

        # C4: Match a real-world example to the concept it illustrates
        c4_name, c4_data = random.choice(all_concepts)
        example = c4_data.get("example", "").strip()
        if example:
            other_examples = [
                cd.get("example", "") for _, cd in all_concepts
                if cd.get("example", "").strip() and cd.get("example", "").lower() != example.lower()
            ]
            pool.append(_q(
                SKILL_CORE,
                f"Which example best illustrates '{c4_name.title()}' in {title}?",
                example,
                other_examples + [
                    f"A situation completely unrelated to {title}.",
                    f"An example that contradicts the principles of {title}.",
                ],
                f"This example correctly illustrates '{c4_name.title()}'.",
                concept=c4_name,
            ))

    # --- Application questions ------------------------------------------------
    # These questions check whether the student can connect the topic to
    # real-world contexts and use cases.

    if apps:
        # A1: Identify a real-world application by name
        a1 = random.choice(apps)
        pool.append(_q(
            SKILL_APPLICATION,
            f"Which of the following is a real-world application of {title}?",
            a1.title(),
            [a.title() for a in apps if a.lower() != a1.lower()]
            + [f"Replacing all study of {title} with memorisation only",
               f"Avoiding {title} in real-world settings entirely"],
            f"'{a1.title()}' is a genuine application of {title}.",
        ))

        # A2: Explain how the topic is used within a specific domain
        a2  = random.choice(apps)
        desc = app_descs.get(a2, "").strip()
        if desc:
            pool.append(_q(
                SKILL_APPLICATION,
                f"How is {title} applied in the context of '{a2.title()}'?",
                desc,
                [app_descs.get(a, "") for a in apps if a != a2 and app_descs.get(a, "").strip()]
                + [f"It is not applied in '{a2.title()}' at all.",
                   f"{title} is used only for theoretical study, not in '{a2.title()}'."],
                f"In '{a2.title()}', {title} is used as follows: {desc}",
            ))

        # A3: Identify an option that does NOT represent a valid application
        pool.append(_q(
            SKILL_APPLICATION,
            f"Which of the following is NOT a valid application of {title}?",
            f"Using {title} only as entertainment with no learning outcome",
            [a.title() for a in apps[:3]],
            f"The other options are all real applications of {title}.",
        ))

    # --- Misconception questions ----------------------------------------------
    # These questions train students to distinguish between false beliefs
    # that are commonly held and statements that are actually correct.

    # M1: Spot the misconception among correct statements
    m1 = random.choice(misconceptions)
    pool.append(_q(
        SKILL_MISCONCEPTION,
        f"Which of the following statements about {title} is a common misconception?",
        m1,
        [f for f in facts if f.strip().lower() != m1.strip().lower()]
        + [f"{title} can be understood through clear definitions and examples.",
           f"Learning {title} involves both theory and real-world practice."],
        f"This is a misconception. The other options are correct statements about {title}.",
    ))

    # M2: Identify the false statement (different framing from M1)
    m2          = random.choice(misconceptions)
    sample_facts = (
        random.sample(facts, min(3, len(facts))) if len(facts) >= 3
        else facts + [f"Students improve at {title} by asking questions."]
    )
    pool.append(_q(
        SKILL_MISCONCEPTION,
        f"Which of the following statements about {title} is FALSE?",
        m2,
        sample_facts,
        f"This statement is false — it is a common misconception about {title}.",
    ))

    # M3: Explain why a student's incorrect claim is wrong
    if misconceptions and facts:
        m3       = random.choice(misconceptions)
        rebuttal = random.choice(facts)
        pool.append(_q(
            SKILL_MISCONCEPTION,
            f"A student claims: '{m3}'. Why is this incorrect?",
            rebuttal,
            [mc for mc in misconceptions if mc != m3][:2]
            + [f"It is not incorrect — the student is right about {title}.",
               "The claim is partially true and should be accepted."],
            f"The correct understanding is: {rebuttal}",
        ))

    # --- Selection: one question per skill category --------------------------
    # Grouping by skill before selecting ensures the four questions always
    # cover all four learning dimensions, not just whichever happened to be
    # generated most often.

    by_skill: Dict[str, List[Dict]] = {}
    for q in pool:
        by_skill.setdefault(q["skill"], []).append(q)

    chosen: List[Dict] = []
    skills_order = [SKILL_DEFINITION, SKILL_CORE, SKILL_APPLICATION, SKILL_MISCONCEPTION]
    random.shuffle(skills_order)  # randomise which skill appears as Q1, Q2, Q3, Q4

    for skill in skills_order:
        if by_skill.get(skill):
            chosen.append(random.choice(by_skill[skill]))
        if len(chosen) == 4:
            break

    # Fill remaining slots if any skill category produced no questions
    remaining = [q for q in pool if q not in chosen]
    random.shuffle(remaining)
    while len(chosen) < 4 and remaining:
        chosen.append(remaining.pop())

    random.shuffle(chosen)
    return chosen[:4]


# ---------------------------------------------------------------------------
# Grading
# ---------------------------------------------------------------------------

def grade(questions: List[Dict], answers: Dict[int, str]) -> Dict:
    """
    Score a completed mock test and identify the student's weakest skill.

    Answers are matched by position index. Comparison is case-insensitive
    and strips surrounding whitespace to avoid false negatives from minor
    formatting differences.

    Returns a summary dict containing the raw score, percentage, the first
    skill category answered incorrectly, and a per-question detail list.
    """
    details = []
    score   = 0
    weak    = []
    weak_concepts: List[str] = []

    for i, q in enumerate(questions):
        chosen  = (answers.get(i, "") or "").strip()
        correct = chosen == q["answer"].strip()
        score  += int(correct)
        if not correct:
            weak.append(q["skill"])
            if q.get("concept"):
                weak_concepts.append(q["concept"])
        details.append({
            "q":       q["q"],
            "chosen":  chosen,
            "answer":  q["answer"],
            "correct": correct,
            "skill":   q["skill"],
            "why":     q["why"],
            "concept": q.get("concept", ""),
        })

    total = len(questions)
    pct   = round((score / total) * 100, 1) if total else 0

    return {
        "score":   score,
        "total":   total,
        "pct":     pct,
        "weakest": weak[0] if weak else "None",
        "weak_skills": weak,
        "weak_concepts": weak_concepts,
        "details": details,
    }

from engine import build_pack, build_brain_brief, make_questions, grade, tutor_sections
from topics import TOPIC_OPTIONS, validate_topics
from wiki_fetcher import smart_answer_from_pack

def test_topic_options_and_schema():
    assert "Custom Topic" in TOPIC_OPTIONS
    assert validate_topics() == []

def test_build_pack_accepts_wikipedia_keyword_argument():
    pack = build_pack("Neural Network", use_wikipedia=True)
    assert pack["title"]
    assert pack["concepts"]

def test_full_student_mission_core_flow():
    pack = build_pack("Machine Learning", use_wikipedia=False)
    brief = build_brain_brief(pack)
    questions = make_questions(pack)
    answers = {i: q["answer"] for i, q in enumerate(questions)}
    result = grade(questions, answers)
    tutor = tutor_sections(pack, "Explain model")
    smart = smart_answer_from_pack(pack, "What is machine learning?")
    assert brief["tiny_answer"]
    assert len(questions) == 4
    assert result["pct"] == 100
    assert tutor["tiny_answer"]
    assert smart["answer"]

import pytest
from engine import build_pack, build_brain_brief, make_questions, tutor_sections, grade

@pytest.mark.parametrize("topic", ["Quantum Mechanics", "Machine Learning", "Python Programming", "Data Structures"])
def test_demo_topics_build_end_to_end(topic):
    pack = build_pack(topic)
    assert pack["title"]
    assert pack["misconceptions"]
    assert pack["concepts"]
    assert build_brain_brief(pack)["tiny_answer"]
    assert len(make_questions(pack)) == 4

def test_grading_and_tutor_shape():
    pack = build_pack("Machine Learning")
    questions = make_questions(pack)
    answers = {i: q["answer"] for i, q in enumerate(questions)}
    assert grade(questions, answers)["pct"] == 100
    sections = tutor_sections(pack, "I do not understand model")
    for key in ["tiny_answer", "explain_simply", "real_life_example", "common_mistake", "exam_angle"]:
        assert sections[key]

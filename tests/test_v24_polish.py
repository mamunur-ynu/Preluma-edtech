from pathlib import Path
from llm import detect_topic_from_question

def test_machine_learning_topic_priority():
    assert detect_topic_from_question("Explain machine learning simply", "Variance") == "Machine Learning"

def test_v24_ui_sections_exist():
    text=Path("streamlit_app.py").read_text(encoding="utf-8")
    for value in ["nav-label","team-photo-hero","_question_needs_clarification","_natural_answer_text","Answer depth"]:
        assert value in text

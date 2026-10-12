from llm import detect_topic_from_question
from views.ai_tutor_legacy import _natural_answer_text, _question_needs_clarification

def test_machine_learning_topic_priority():
    assert detect_topic_from_question("Explain machine learning simply", "Variance") == "Machine Learning"

def test_vague_questions_request_clarification_but_real_questions_do_not():
    assert _question_needs_clarification("hello, can you help?")
    assert _question_needs_clarification("explain")
    assert not _question_needs_clarification("How does gradient descent update model weights?")


def test_answer_depth_changes_the_rendered_information():
    response = {
        "tiny_answer": "Direct.",
        "explain_simply": "Explanation.",
        "real_life_example": "Example.",
        "common_mistake": "Mistake.",
        "exam_angle": "Exam.",
    }
    short = _natural_answer_text(response, "Short")
    deep = _natural_answer_text(response, "Deep")
    assert short.count("\n\n") == 1
    assert deep.count("\n\n") == 4
    assert "Exam." not in short and "Exam." in deep

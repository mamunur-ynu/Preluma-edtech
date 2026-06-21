from pathlib import Path
import homework_core as hw


def redirect_files(tmp_path: Path) -> None:
    hw.DATA_DIR = tmp_path / "data"
    hw.HOMEWORK_CSV = hw.DATA_DIR / "homework.csv"
    hw.QUESTIONS_CSV = hw.DATA_DIR / "homework_questions.csv"
    hw.SUBMISSIONS_CSV = hw.DATA_DIR / "homework_submissions.csv"
    hw.MISTAKES_CSV = hw.DATA_DIR / "student_mistakes.csv"
    hw.NOTIFICATIONS_CSV = hw.DATA_DIR / "notifications.csv"


def test_homework_end_to_end(tmp_path):
    redirect_files(tmp_path)
    homework_id = hw.create_homework(
        title="Test Homework",
        topic="Python",
        instructions="Answer all questions.",
        due_date="Friday",
        difficulty="Beginner",
        assigned_to="Mim",
        created_by="Teacher",
        questions=[
            {
                "question": "What is a function?",
                "options": ["Reusable code", "A picture", "A file only", "Nothing"],
                "answer": "Reusable code",
                "concept": "Function",
                "explanation": "A function is reusable code.",
                "marks": 1,
            }
        ],
    )

    assert hw.homework_for_student("Mim")[0]["Title"] == "Test Homework"
    assert len(hw.notifications_for_student("Mim")) == 1

    result = hw.submit_homework(
        homework_id,
        "Mim",
        {1: "A picture"},
    )
    assert result["percentage"] == 0.0
    assert len(result["mistakes"]) == 1
    assert hw.load_student_mistakes("Mim")[0]["Weak Concept"] == "Function"

    report = hw.homework_overview(homework_id)
    assert report["submissions"] == 1
    assert report["common_weak_concept"] == "Function"

"""Student homework page and the teacher Homework Center."""

from __future__ import annotations


import streamlit as st

from components import progress_hooks

from services.user_service import student_number_by_name

from components.ui_components import page_intro
from services.homework_service import create_homework
from services.homework_service import homework_for_student
from services.homework_service import homework_overview
from services.homework_service import hw_num
from services.homework_service import load_homework
from services.homework_service import load_questions
from services.homework_service import load_student_mistakes
from services.homework_service import load_submissions
from services.homework_service import mark_notifications_read
from services.homework_service import notifications_for_student
from services.homework_service import submit_homework
from services.ai_service import homework_tutor_intro as llm_hw_tutor_intro
from services.ai_service import homework_tutor_reply as llm_hw_tutor_reply
from services.upload_service import HOMEWORK_POLICY, store_private_upload

def my_homework_page():
    """
    Render the student homework page.

    Shows all homework assignments that have been assigned to the student or
    to 'All Students'. The student can:
      - View the question set and attempt an assignment.
      - Review their previous submissions with per-question feedback.
      - Access the AI homework tutor for help with any concept.

    Correct answers are shown only after the student submits, and mistakes
    are logged to the mistakes file for the teacher's analytics panel.
    """
    student = st.session_state.get("student", "Student")

    page_intro(
        "homework",
        "Student assignment desk",
        "My Homework",
        "Complete your assigned work, question by question. Each answer is reviewed instantly.",
    )

    # Notifications
    notifications = notifications_for_student(student)
    if notifications:
        unread = [n for n in notifications if n.get("Is Read") == "No"]
        label = f"Notifications ({len(notifications)})"
        if unread:
            label += f" -- {len(unread)} new"
        with st.expander(label, expanded=bool(unread)):
            for note in reversed(notifications[-6:]):
                is_new = note.get("Is Read") == "No"
                dot = (
                    "<span style='width:7px;height:7px;border-radius:50%;"
                    "background:#f87171;display:inline-block;margin-right:7px;'></span>"
                    if is_new else ""
                )
                st.markdown(
                    f"<div class='assignment-card'>"
                    f"<div class='albl lbl-blue' style='display:flex;align-items:center;'>"
                    f"{dot}{note.get('Title', '')}</div>"
                    f"<div class='atxt' style='margin-top:6px;'>{note.get('Message', '')}"
                    f"</div></div>",
                    unsafe_allow_html=True,
                )
            if unread:
                if st.button("Mark all as read", key="mark_read_btn"):
                    mark_notifications_read(student)
                    st.rerun()

    homework_rows = homework_for_student(student)
    if not homework_rows:
        st.info("No homework assigned yet. Check back after your teacher publishes an assignment.")
        return

    # Homework selector
    labels = {
        f"#{hw_num(row)} · {row['Title']} · Due {row['Due Date']}": row
        for row in homework_rows
    }
    selected_label = st.selectbox("Choose assignment", list(labels))
    selected = labels[selected_label]
    homework_id = selected["Homework ID"]

    # Reset step when homework changes
    if st.session_state.get("_hw_active_id") != homework_id:
        st.session_state["_hw_q_step"] = 0
        st.session_state["_hw_answers"] = {}
        st.session_state["homework_result"] = None
        st.session_state["_hw_active_id"] = homework_id
        st.session_state["_hw_study_mode"] = False
        st.session_state["_hw_chat_history"] = []

    # Assignment info card
    _cb = selected.get('Created By', '') or ''
    _att = selected.get('Attachment', '') or ''
    _teacher_badge = (
        f"<span style='font-size:12px;color:#64748b;'>Assigned by: "
        f"<b style='color:#38bdf8;'>{_cb}</b></span>"
        if _cb else ""
    )
    _att_badge = (
        f"<span style='font-size:12px;color:#64748b;margin-left:16px;'>📎 "
        f"<b style='color:#a5b4fc;'>{_att}</b></span>"
        if _att else ""
    )
    st.markdown(
        f"<div style='background:linear-gradient(145deg,rgba(120,53,15,.22),rgba(12,18,29,.92));"
        f"border:1px solid rgba(245,158,11,.20);border-radius:20px;padding:20px 24px;margin:10px 0 20px;'>"
        f"<div style='font-size:10px;font-weight:800;color:#f59e0b;letter-spacing:.12em;"
        f"text-transform:uppercase;margin-bottom:8px;'>{selected.get('Topic', '')}</div>"
        f"<div style='font-size:17px;font-weight:800;color:#f8fafc;margin-bottom:6px;'>"
        f"{selected.get('Title', '')}</div>"
        f"<div style='font-size:13px;color:#94a3b8;margin-bottom:10px;'>{selected.get('Instructions', '')}</div>"
        f"<div style='display:flex;gap:16px;flex-wrap:wrap;'>"
        f"<span style='font-size:12px;color:#64748b;'>Due: <b style='color:#fbbf24;'>"
        f"{selected.get('Due Date', '')}</b></span>"
        f"<span style='font-size:12px;color:#64748b;'>Difficulty: <b style='color:#fbbf24;'>"
        f"{selected.get('Difficulty', '')}</b></span>"
        f"{_teacher_badge}{_att_badge}"
        f"</div></div>",
        unsafe_allow_html=True,
    )

    questions = load_questions(homework_id)
    total_q = len(questions)

    # Check if student already submitted this homework (permanent one-attempt rule)
    _student_key = student.strip().casefold()
    _existing = [
        r for r in load_submissions(homework_id)
        if str(r.get("Student", "")).strip().casefold() == _student_key
    ]
    if _existing and not st.session_state.get("homework_result"):
        # Already submitted -- load their most recent result into session so the
        # scoreboard renders, but mark it as read-only (no retry allowed)
        _last = _existing[0]
        st.session_state["homework_result"] = {
            "percentage": float(_last.get("Percentage", 0)),
            "score":      int(_last.get("Score", 0)),
            "total":      int(_last.get("Total", total_q)),
            "attempt":    int(_last.get("Attempt", 1)),
            "details":    [],   # no detail breakdown from DB -- show summary only
            "_read_only": True,
        }

    result = st.session_state.get("homework_result")

    # RESULTS / SCOREBOARD view
    if result:
        pct    = result.get("percentage", 0)
        score  = result.get("score", 0)
        total  = result.get("total", total_q)
        attempt = result.get("attempt", 1)
        mistakes_list = [d for d in result.get("details", []) if not d["correct"]]
        has_mistakes  = bool(mistakes_list)

        # Grade colour + message
        if pct == 100:
            grade_color = "#34d399"
            verdict     = "Perfect Score! 🎯 Outstanding work!"
            sub_msg     = "You answered everything correctly. Homework submitted!"
        elif pct >= 80:
            grade_color = "#34d399"
            verdict     = "Excellent Work! 🌟"
            sub_msg     = "Great job -- homework submitted. Review the missed questions below."
        elif pct >= 60:
            grade_color = "#fbbf24"
            verdict     = "Good Effort! 👍"
            sub_msg     = "Homework submitted. Try again to improve your score."
        elif pct >= 40:
            grade_color = "#fbbf24"
            verdict     = "Keep Going 💪"
            sub_msg     = "Homework submitted. Review the concepts below and try again."
        else:
            grade_color = "#f87171"
            verdict     = "Needs Review 📚"
            sub_msg     = "Homework submitted. Study the explanations and try again."

        st.markdown(
            f"<div style='background:linear-gradient(135deg,rgba(15,23,42,.95),rgba(8,14,26,.98));"
            f"border:2px solid {grade_color}44;border-radius:24px;padding:32px 28px;"
            f"text-align:center;margin-bottom:24px;'>"
            f"<div style='font-size:64px;font-weight:900;color:{grade_color};line-height:1;"
            f"text-shadow:0 0 30px {grade_color}66;'>{pct}%</div>"
            f"<div style='font-size:15px;color:#94a3b8;margin-top:8px;'>"
            f"{score} / {total} correct &nbsp;&bull;&nbsp; Attempt {attempt}</div>"
            f"<div style='margin-top:12px;display:inline-block;background:{grade_color}20;"
            f"border:1px solid {grade_color}50;border-radius:30px;padding:6px 20px;"
            f"color:{grade_color};font-size:13px;font-weight:700;'>{verdict}</div>"
            f"<div style='margin-top:10px;font-size:12px;color:#64748b;'>{sub_msg}</div>"
            f"</div>",
            unsafe_allow_html=True,
        )

        # Show only wrong answers (nothing to show for 100%)
        for detail in result.get("details", []):
            ok = detail["correct"]
            if ok:
                continue  # skip correct answers in review
            st.markdown(
                f"<div style='background:rgba(248,113,113,.08);border:1px solid rgba(248,113,113,.25);"
                f"border-radius:16px;padding:16px 18px;margin:8px 0;'>"
                f"<div style='font-size:11px;font-weight:800;color:#94a3b8;letter-spacing:.08em;"
                f"text-transform:uppercase;margin-bottom:6px;'>{detail['concept']}</div>"
                f"<div style='font-size:14px;color:#e2e8f0;margin-bottom:10px;'>"
                f"{detail.get('question', '')}</div>"
                f"<div style='font-size:13px;color:#94a3b8;'>Your answer: "
                f"<b style='color:#f87171;'>{detail.get('chosen', '')}</b></div>"
                f"<div style='font-size:13px;color:#94a3b8;margin-top:4px;'>Correct: "
                f"<b style='color:#34d399;'>{detail.get('correct_answer', '')}</b></div>"
                f"<div style='font-size:12px;color:#64748b;margin-top:8px;'>"
                f"{detail.get('explanation', '')}</div></div>",
                unsafe_allow_html=True,
            )

        # Action button -- only "Study with Preluma AI" if score < 80%, nothing for perfect
        read_only = result.get("_read_only", False)
        if pct < 80:
            st.markdown("<div style='height:8px;'></div>", unsafe_allow_html=True)
            _hw_topic = selected.get("Topic", "")
            _hw_weak  = [d["concept"] for d in mistakes_list] if mistakes_list else [_hw_topic]

            if not st.session_state.get("_hw_study_mode"):
                if st.button("🤖 Study this topic with Preluma AI", use_container_width=True, type="primary"):
                    st.session_state["_hw_study_mode"]   = True
                    st.session_state["_hw_chat_topic"]   = _hw_topic
                    st.session_state["_hw_chat_weak"]    = _hw_weak
                    st.session_state["_hw_chat_history"] = []
                    # Generate opening explanation immediately
                    with st.spinner("Preluma AI is preparing your study session..."):
                        intro = llm_hw_tutor_intro(_hw_topic, _hw_weak, pct)
                    st.session_state["_hw_chat_history"].append({"role": "ai", "text": intro})
                    st.rerun()

        elif pct == 100 and not read_only:
            st.markdown(
                "<div style='text-align:center;font-size:12px;color:#475569;margin-top:4px;'>"
                "No further action needed -- great work!</div>",
                unsafe_allow_html=True,
            )

        # ── Inline Homework AI Tutor ──────────────────────────────────────────
        if st.session_state.get("_hw_study_mode"):
            _hw_topic = st.session_state.get("_hw_chat_topic", selected.get("Topic", ""))
            _hw_weak  = st.session_state.get("_hw_chat_weak", [])
            _history  = st.session_state.get("_hw_chat_history", [])

            st.markdown("<div style='height:20px;'></div>", unsafe_allow_html=True)
            st.markdown("""
            <div style='background:linear-gradient(135deg,rgba(56,189,248,.08),rgba(99,102,241,.08));
                        border:1px solid rgba(56,189,248,.20);border-radius:20px;
                        padding:16px 20px 10px;margin-bottom:4px;'>
              <div style='font-size:11px;font-weight:800;color:#38bdf8;letter-spacing:.10em;
                          text-transform:uppercase;margin-bottom:2px;'>🤖 Preluma AI Study Session</div>
              <div style='font-size:12px;color:#64748b;'>Ask anything about this topic -- I'll explain until you understand.</div>
            </div>""", unsafe_allow_html=True)

            # Chat history
            for msg in _history:
                if msg["role"] == "ai":
                    st.markdown(f"""
                    <div style='background:rgba(56,189,248,.07);border:1px solid rgba(56,189,248,.15);
                                border-radius:16px 16px 16px 4px;padding:14px 18px;margin:10px 0 6px;
                                font-size:14px;color:#cbd5e1;line-height:1.75;'>
                      <span style='font-size:11px;font-weight:700;color:#38bdf8;letter-spacing:.06em;
                                   display:block;margin-bottom:8px;'>PRELUMA AI</span>
                      {msg["text"].replace(chr(10), "<br>")}
                    </div>""", unsafe_allow_html=True)
                else:
                    st.markdown(f"""
                    <div style='background:rgba(99,102,241,.08);border:1px solid rgba(99,102,241,.18);
                                border-radius:16px 16px 4px 16px;padding:12px 18px;margin:6px 0 6px 40px;
                                font-size:14px;color:#e2e8f0;line-height:1.65;text-align:right;'>
                      <span style='font-size:11px;font-weight:700;color:#818cf8;letter-spacing:.06em;
                                   display:block;margin-bottom:6px;'>YOU</span>
                      {msg["text"]}
                    </div>""", unsafe_allow_html=True)

            # Input box
            st.markdown("<div style='height:6px;'></div>", unsafe_allow_html=True)
            _q = st.text_area(
                "Ask your question",
                key=f"_hw_tutor_input_{st.session_state.get('_hw_input_key', 0)}",
                placeholder=f"E.g. 'Can you explain {_hw_topic} with a real example?' or 'I still don't understand -- can you say it differently?'",
                height=90,
                label_visibility="collapsed",
            )
            _col1, _col2 = st.columns([5, 1])
            _send = _col1.button("Send →", use_container_width=True, type="primary", key="hw_tutor_send")
            _close = _col2.button("✕ Close", use_container_width=True, key="hw_tutor_close")

            if _close:
                st.session_state["_hw_study_mode"]   = False
                st.session_state["_hw_chat_history"] = []
                st.rerun()

            if _send and _q.strip():
                _history.append({"role": "student", "text": _q.strip()})
                with st.spinner("Preluma AI is thinking..."):
                    _reply = llm_hw_tutor_reply(_hw_topic, _hw_weak, _history, _q.strip())
                _history.append({"role": "ai", "text": _reply})
                st.session_state["_hw_chat_history"] = _history
                # Clear the input box before rerun (counter pattern avoids StreamlitAPIException)
                st.session_state["_hw_input_key"] = st.session_state.get("_hw_input_key", 0) + 1
                st.rerun()

        return

    # Sequential Q&A
    if not questions:
        st.info("No questions found for this assignment.")
        return

    q_step   = min(st.session_state.get("_hw_q_step", 0), total_q - 1)
    hw_answers = st.session_state.get("_hw_answers", {})
    question = questions[q_step]
    q_id     = int(question["Question ID"])
    is_last  = (q_step == total_q - 1)

    # Progress bar
    pct_done = int((q_step / total_q) * 100)
    st.markdown(
        f"<div style='margin-bottom:18px;'>"
        f"<div style='display:flex;justify-content:space-between;align-items:center;margin-bottom:8px;'>"
        f"<span style='font-size:12px;font-weight:700;color:#64748b;letter-spacing:.06em;"
        f"text-transform:uppercase;'>Question {q_step + 1} of {total_q}</span>"
        f"<span style='font-size:12px;color:#38bdf8;font-weight:700;'>{pct_done}% done</span></div>"
        f"<div style='background:rgba(30,41,59,.6);border-radius:8px;height:6px;overflow:hidden;'>"
        f"<div style='width:{pct_done}%;height:100%;"
        f"background:linear-gradient(90deg,#0ea5e9,#6366f1);border-radius:8px;'>"
        f"</div></div></div>",
        unsafe_allow_html=True,
    )

    # Question card
    st.markdown(
        f"<div style='background:linear-gradient(145deg,rgba(15,23,42,.94),rgba(8,14,26,.98));"
        f"border:1px solid rgba(99,102,241,.25);border-radius:24px;"
        f"padding:28px 28px 22px;margin-bottom:18px;"
        f"box-shadow:0 16px 50px rgba(0,0,0,.30);'>"
        f"<div style='display:flex;align-items:center;gap:10px;margin-bottom:18px;'>"
        f"<div style='width:36px;height:36px;border-radius:10px;"
        f"background:linear-gradient(135deg,#6366f1,#8b5cf6);"
        f"display:flex;align-items:center;justify-content:center;"
        f"font-size:14px;font-weight:900;color:#fff;flex-shrink:0;'>Q{q_step + 1}</div>"
        f"<div style='font-size:11px;font-weight:800;color:#a78bfa;letter-spacing:.09em;"
        f"text-transform:uppercase;'>{question.get('Concept', '')}</div></div>"
        f"<div style='font-size:17px;font-weight:700;color:#f1f5f9;line-height:1.55;'>"
        f"{question.get('Question', '')}</div></div>",
        unsafe_allow_html=True,
    )

    options = question.get("Options", [])
    prev_answer = hw_answers.get(q_id)
    default_idx = options.index(prev_answer) if prev_answer in options else None

    chosen = st.radio(
        "Select your answer",
        options,
        index=default_idx,
        key=f"hw_radio_{homework_id}_{q_step}",
        label_visibility="collapsed",
    )

    col1, col2 = st.columns([1, 2])
    if q_step > 0:
        if col1.button("Previous", use_container_width=True):
            hw_answers[q_id] = chosen if chosen is not None else ""
            st.session_state["_hw_answers"] = hw_answers
            st.session_state["_hw_q_step"] = q_step - 1
            st.rerun()

    if not is_last:
        if col2.button("Next Question", use_container_width=True, type="primary"):
            hw_answers[q_id] = chosen if chosen is not None else ""
            st.session_state["_hw_answers"] = hw_answers
            st.session_state["_hw_q_step"] = q_step + 1
            st.rerun()
    else:
        if col2.button("Submit Homework", use_container_width=True, type="primary"):
            hw_answers[q_id] = chosen if chosen is not None else ""
            st.session_state["_hw_answers"] = hw_answers
            final_answers = {int(k): v for k, v in hw_answers.items()}
            result = submit_homework(homework_id, student, final_answers)
            progress_hooks.record_homework(result, str(selected.get("Topic", "")))
            st.session_state["homework_result"] = result
            st.rerun()

    # Weak areas history
    mistakes = load_student_mistakes(student)
    if mistakes:
        with st.expander("My previous weak areas"):
            for mistake in mistakes[-6:]:
                st.markdown(
                    f"<div style='font-size:13px;color:#64748b;padding:4px 0;"
                    f"border-bottom:1px solid rgba(255,255,255,.04);'>"
                    f"<b style='color:#f87171;'>{mistake.get('Weak Concept', '')}</b> -- "
                    f"{mistake.get('Question', '')}</div>",
                    unsafe_allow_html=True,
                )


def default_homework_questions(topic: str) -> list[dict]:
    """7 default questions covering definition, application, example, analysis,
    comparison, reflection, and exam readiness."""
    return [
        {
            "question": f"What is the most accurate definition of {topic}?",
            "options": [
                f"The core meaning and purpose of {topic}",
                "A random process unrelated to the subject",
                "Only a complex formula with no meaning",
                "Something that cannot be explained simply",
            ],
            "answer": f"The core meaning and purpose of {topic}",
            "concept": "Definition",
            "explanation": "Always start with the clear definition before exploring deeper details.",
            "marks": 1,
        },
        {
            "question": f"Which approach best helps a student understand {topic}?",
            "options": [
                "Connect the definition with a real-world example",
                "Memorize keywords without understanding",
                "Skip the basics and jump to advanced parts",
                "Avoid asking questions during class",
            ],
            "answer": "Connect the definition with a real-world example",
            "concept": "Learning Strategy",
            "explanation": "Real examples bridge theory and practice -- they make abstract ideas concrete.",
            "marks": 1,
        },
        {
            "question": f"Which is a real-world application of {topic}?",
            "options": [
                f"Using {topic} principles to solve a practical problem",
                "Memorizing a single sentence about it",
                "Ignoring it until the exam",
                "Replacing it with an unrelated concept",
            ],
            "answer": f"Using {topic} principles to solve a practical problem",
            "concept": "Application",
            "explanation": "Application shows you understand not just what it is, but how and why it is used.",
            "marks": 1,
        },
        {
            "question": f"What is a common misconception students have about {topic}?",
            "options": [
                "That it is more complex than it needs to be",
                "That it requires no prior knowledge",
                "That it has no real-world use",
                "That it can be fully learned in one minute",
            ],
            "answer": "That it is more complex than it needs to be",
            "concept": "Misconception",
            "explanation": "Breaking false beliefs is a key step in deep understanding.",
            "marks": 1,
        },
        {
            "question": f"How does {topic} relate to other subjects or topics you have studied?",
            "options": [
                "It builds on prior knowledge and connects to related ideas",
                "It is completely isolated from everything else",
                "It only matters in one very specific exam",
                "It contradicts everything learned before",
            ],
            "answer": "It builds on prior knowledge and connects to related ideas",
            "concept": "Connection",
            "explanation": "Strong learners see connections between topics -- this creates a knowledge network.",
            "marks": 1,
        },
        {
            "question": f"What should a student do after making a mistake in a {topic} question?",
            "options": [
                "Review the weak concept and attempt a similar question",
                "Ignore the mistake and move on",
                "Stop studying the topic entirely",
                "Choose random answers next time",
            ],
            "answer": "Review the weak concept and attempt a similar question",
            "concept": "Reflection",
            "explanation": "Mistakes guide the next learning action -- they are most useful when reviewed.",
            "marks": 1,
        },
        {
            "question": f"If asked to explain {topic} in a university exam, which answer is best?",
            "options": [
                "Define it clearly, give one example, and state why it matters",
                "Write only the name of the topic",
                "Copy a formula without explaining what it means",
                "Say it is too difficult to explain",
            ],
            "answer": "Define it clearly, give one example, and state why it matters",
            "concept": "Exam Readiness",
            "explanation": "Exam answers must show understanding: definition + example + significance.",
            "marks": 1,
        },
    ]


def homework_center_page():
    """
    Render the teacher Homework Center page.

    Provides two tabs:
      Create Homework — a form for writing a title, topic, instructions,
        due date, and difficulty level. Questions are generated automatically
        by engine or entered manually. The form also accepts an optional file
        attachment and a target student selection.
      Class Overview — a summary of all submissions grouped by assignment,
        showing average scores, weakest concepts, and individual student
        results so the teacher can identify which topics need review.
    """
    _TEACHER_OPTIONS = [
        "Zhou Yujue (周玉珏) · AI Dept",
        "Gao Song (高嵩) · Software Engineering",
        "Tang Li (唐丽) · Cyberspace Security",
        "Wei Ping (韦平) · Cyberspace Security",
    ]
    _TEACHER_NAMES = {
        "Zhou Yujue (周玉珏) · AI Dept":              "Zhou Yujue",
        "Gao Song (高嵩) · Software Engineering":     "Gao Song",
        "Tang Li (唐丽) · Cyberspace Security":        "Tang Li",
        "Wei Ping (韦平) · Cyberspace Security":       "Wei Ping",
    }
    # Auto-select teacher from logged-in user if they match
    _logged_name = st.session_state.get("student", "") or ""
    _default_teacher_idx = 0
    for i, k in enumerate(_TEACHER_OPTIONS):
        if any(n in _logged_name for n in ["Zhou","Gao","Tang","Wei"]):
            if _logged_name.split()[0] in k:
                _default_teacher_idx = i

    page_intro(
        "homework",
        "Teacher assignment workspace",
        "Homework Center",
        "Create assignments, publish them to students, and review class submission patterns and weak concepts.",
    )

    create_tab, overview_tab = st.tabs(["Create Homework", "Class Overview"])

    with create_tab:
        # File uploader must live outside the form to allow re-upload without submit
        uploaded_file = st.file_uploader(
            "Attach homework file (optional)",
            type=["pdf", "doc", "docx", "txt"],
            help="Upload a PDF or Word document as the homework reference material.",
            key="hw_file_upload",
        )
        attachment_name = ""
        if uploaded_file is not None:
            try:
                stored = store_private_upload(
                    "homework_attachments", uploaded_file.name, uploaded_file.getvalue(), HOMEWORK_POLICY
                )
                attachment_name = stored.relative_path
                st.success(f"📎 File ready: {stored.filename}")
            except ValueError as exc:
                st.error(str(exc))

        with st.form("teacher_homework_creator", border=False):
            # Teacher selector
            teacher_sel = st.selectbox(
                "Assigned by (Teacher)",
                _TEACHER_OPTIONS,
                index=_default_teacher_idx,
                help="Select which teacher is publishing this homework.",
            )
            c1, c2 = st.columns(2)
            title = c1.text_input("Homework title", value="Introduction Practice")
            topic = c2.text_input("Topic", value="Machine Learning")
            instructions = st.text_area(
                "Instructions",
                value="Read the topic summary and answer all questions.",
            )
            c3, c4, c5 = st.columns(3)
            due_date = c3.text_input("Due date", value="Friday 8:00 PM")
            difficulty = c4.selectbox("Difficulty", ["Beginner", "Intermediate", "Advanced"])
            assigned_to = c5.text_input(
                "Assign to",
                value="All Students",
                help="Use All Students or comma-separated student names.",
            )
            publish = st.form_submit_button("Publish Homework", use_container_width=True)

        if publish:
            teacher_display = teacher_sel
            teacher_name    = _TEACHER_NAMES.get(teacher_sel, teacher_sel)
            homework_id, new_hw_number = create_homework(
                title=title,
                topic=topic,
                instructions=instructions,
                due_date=due_date,
                difficulty=difficulty,
                assigned_to=assigned_to,
                created_by=teacher_display,
                questions=default_homework_questions(topic),
                attachment=attachment_name,
            )
            st.success(f"✅ Homework #{new_hw_number} published by **{teacher_name}**. Students have been notified.")

    with overview_tab:
        rows = load_homework()
        if not rows:
            st.info("No homework is available.")
        else:
            labels = {
                f"#{hw_num(row)} · {row['Title']}": row
                for row in rows
            }
            selected_label = st.selectbox(
                "Homework report",
                list(labels),
                key="teacher_homework_report",
            )
            selected = labels[selected_label]
            report = homework_overview(selected["Homework ID"])

            c1, c2, c3, c4 = st.columns(4)
            c1.metric("Submissions", report["submissions"])
            c2.metric("Average", f"{report['average']}%")
            c3.metric("Highest", f"{report['highest']}%")
            c4.metric("Lowest", f"{report['lowest']}%")

            st.markdown(
                f"<div class='card-glass'><div class='albl lbl-red'>"
                f"Most common weak concept</div><div class='atxt'>"
                f"{report['common_weak_concept']} "
                f"({report['common_weak_count']} captured mistakes)</div></div>",
                unsafe_allow_html=True,
            )
            # Clean submission table -- show student name+ID, score, date; hide UUIDs
            _clean_rows = []
            for _s in report["submission_rows"]:
                _sname = str(_s.get("Student", ""))
                _snum  = student_number_by_name(_sname)
                _label = f"{_sname} (#{_snum})" if _snum else _sname
                _clean_rows.append({
                    "Student":        _label,
                    "Score":          f"{_s.get('Score',0)}/{_s.get('Total',0)}",
                    "Percentage (%)": _s.get("Percentage", 0),
                    "Attempt":        _s.get("Attempt", 1),
                    "Submitted At":   str(_s.get("Submitted At", ""))[:16],
                    "Status":         _s.get("Status", "Submitted"),
                })
            st.dataframe(_clean_rows, use_container_width=True)

"""Project showcase pages: Evidence Board, Professor Defense, About Us, Demo Guide, Roadmap."""

from __future__ import annotations


import pandas as pd
import streamlit as st

from components.theme import TEAM_URI
from components.ui_components import page_intro
from topics import validate_topics

def evidence_board():
    page_intro(
        "evidence",
        "Project proof and technical validation",
        "Evidence Board",
        "Every Python concept, algorithm, AI integration, and data quality check used in Preluma -- proven and documented.",
    )

    st.markdown("""<div class='ev-grid'>
      <div class='ev-card'><h4>Clear Problem</h4><p>Students enter lectures unprepared, leading to passive learning and poor retention. Preluma solves this with a structured 5-step AI mission before each class.</p></div>
      <div class='ev-card'><h4>Python Architecture</h4><p>Streamlit, Pandas, Plotly, dicts, session state, forms, CSV, Supabase REST API -- all in modular Python files totalling 5,100+ lines.</p></div>
      <div class='ev-card'><h4>Manual Algorithms</h4><p>Merge Sort O(n log n) and Binary Search O(log n) implemented from scratch -- no library sorting. Nanosecond timing stored in result.txt.</p></div>
      <div class='ev-card'><h4>Multi-LLM AI</h4><p>Claude, Groq, and Gemini with automatic fallback -- whichever key is available is used. 3-Mood system: Normal, Coach, Roast.</p></div>
      <div class='ev-card'><h4>Persistent Storage</h4><p>Supabase REST API stores student records, homework, projects, and profile photos permanently. CSV fallback when Supabase is unavailable.</p></div>
      <div class='ev-card'><h4>Wikipedia Fallback</h4><p>Unknown topics fetch real content from Wikipedia API -- no empty answers, ever. 29 built-in topic packs plus unlimited free-text topics.</p></div>
      <div class='ev-card'><h4>Login & Security</h4><p>HMAC-signed session tokens survive browser refresh with zero network calls. Role-based access: students and teachers see different pages.</p></div>
      <div class='ev-card'><h4>Homework & Projects</h4><p>Teachers publish homework and class projects. Students submit files (up to 100 MB) stored in Supabase -- categorised by type after upload.</p></div>
      <div class='ev-card'><h4>Data Quality Module</h4><p>data_quality.py runs automated checks: topic field validation, CSV schema checks, duplicate detection, and integrity tests -- with nanosecond timing.</p></div>
    </div>""", unsafe_allow_html=True)

    # Live data quality report
    st.markdown(
        "<div style='font-size:11px;font-weight:800;color:#86efac;letter-spacing:.10em;"
        "text-transform:uppercase;margin:24px 0 10px;'>Live Data Quality Report</div>",
        unsafe_allow_html=True,
    )
    if st.button("▶ Run All Checks Now", key="run_dq_btn", type="primary"):
        import data_quality as _dq
        with st.spinner("Running checks..."):
            report = _dq.run_all_checks()
        overall_color = "#34d399" if report["all_passed"] else "#f87171"
        overall_label = "✅ ALL CHECKS PASSED" if report["all_passed"] else "❌ CHECKS FAILED"
        total_ms = report["total_time_ns"] / 1_000_000
        st.markdown(
            f"<div style='background:rgba(52,211,153,.07);border:1px solid rgba(52,211,153,.20);"
            f"border-radius:14px;padding:14px 18px;margin-bottom:12px;'>"
            f"<span style='font-size:15px;font-weight:800;color:{overall_color};'>{overall_label}</span>"
            f"<span style='font-size:12px;color:#475569;margin-left:14px;'>"
            f"{report['total_errors']} error(s) · {report['total_warnings']} warning(s) · {total_ms:.1f} ms</span>"
            f"</div>",
            unsafe_allow_html=True,
        )
        for suite in report["suites"]:
            icon = "✅" if suite["passed"] else "❌"
            suite_ms = suite["time_ns"] / 1_000_000
            with st.expander(f"{icon}  {suite['suite']}  ({suite_ms:.1f} ms)", expanded=not suite["passed"]):
                for e in suite.get("errors", []):
                    st.error(e)
                for w in suite.get("warnings", []):
                    st.warning(w)
                if suite["passed"] and not suite.get("warnings"):
                    st.success("No issues found.")
                for key, label in [("topics_checked","Topics checked"),("files_checked","Files checked"),
                                    ("rows_checked","Rows checked"),("duplicates","Duplicates found")]:
                    if key in suite:
                        st.caption(f"{label}: {suite[key]}")
    else:
        errors = validate_topics()
        if errors:
            st.warning("Topic issues: " + ", ".join(errors[:3]))
        else:
            st.success("All 29 topic packs validated -- no data errors found.")

    st.markdown("### Python Concepts Demonstrated")
    st.dataframe(pd.DataFrame({
        "Concept": ["Functions","Nested Dicts","Session State","Forms","DataFrame","Plotly Charts",
                    "CSV File I/O","Supabase REST API","Wikipedia API","Multi-LLM","Merge Sort",
                    "Binary Search","Audit Log","HMAC Auth","Data Quality Tests"],
        "Used For": ["Modular app logic across 8 Python files","Topic pack storage (29 built-in topics)",
                     "Quiz, tutor, and login state","Safe form submission for homework and projects",
                     "Teacher analytics and class dashboard","Readiness visualisation and score charts",
                     "Local fallback for all data types","Permanent cloud storage for files, photos, projects",
                     "Unknown topic fallback -- no empty answers","Claude/Groq/Gemini auto-select with fallback",
                     "Manual O(n log n) student ranking","Manual O(log n) student search",
                     "Algorithm timing in result.txt (nanoseconds)","Session token signing -- survives browser refresh",
                     "Automated validation for topics, CSVs, duplicates"],
    }), use_container_width=True)


def professor_defense():
    page_intro(
        "defense",
        "Final defense preparation",
        "Professor Defense",
        "Built for final presentation -- clear problem, Python proof, innovation, and contribution.",
    )

    st.markdown("""<div class='rubric-grid'>
      <div class='rubric-card'><h4>1. Real Problem</h4><p>Students enter lectures unprepared, reducing understanding, memory, and class participation.</p></div>
      <div class='rubric-card'><h4>2. Python Solution</h4><p>Preluma uses Python + Streamlit: Brain Brief, quiz, Mistake Clinic, UltraTutor, and dashboard.</p></div>
      <div class='rubric-card'><h4>3. Algorithm Proof</h4><p>Merge Sort (O n log n) and Binary Search (O log n) implemented manually. Timing stored in result.txt.</p></div>
      <div class='rubric-card'><h4>4. Real Data</h4><p>Wikipedia API fallback for unknown topics. CSV persistence for student records. No empty answers.</p></div>
      <div class='rubric-card'><h4>5. AI Integration</h4><p>Claude, Groq, and Gemini -- multi-provider with automatic fallback. Smart question style detection.</p></div>
      <div class='rubric-card'><h4>6. Teacher Value</h4><p>Teacher Studio: readiness analytics, skill gap chart, merge sort ranking, and binary search demo.</p></div>
      <div class='rubric-card'><h4>7. Testing Proof</h4><p>Regression tests verify topic schema, build_pack, quiz flow, tutor output, and QnA.</p></div>
      <div class='rubric-card'><h4>8. Future Product</h4><p>Student accounts, teacher class codes, PDF notes, RAG retrieval, and mobile app roadmap.</p></div>
    </div>""", unsafe_allow_html=True)

    st.markdown("### System Architecture")
    st.code("Student Input → Topic Router → Curated Pack / Wikipedia Fallback → Brain Brief\n→ Quiz (4 skills) → Mistake Clinic → UltraTutor (AI) → Class Questions\n→ CSV Persistence → Merge Sort + Binary Search → Teacher Analytics → Export", language="text")

    st.markdown("### Defense Line")
    st.success("Third-party libraries are allowed. Preluma uses Streamlit and Plotly for the interface, but all core algorithms -- Merge Sort, Binary Search, statistics, CSV I/O -- are implemented manually in Python. This proves both presentation skill and algorithmic understanding.")


def project_team():
    page_intro(
        "defense",
        "Student product team · Yunnan University",
        "Project Team",
        "Three students built Preluma together -- combining core Python development, algorithm testing, and topic data engineering.",
    )

    # Team photo -- full-width, proper fit
    if TEAM_URI:
        st.markdown(
            f"<div style='"
            f"width:100%;border-radius:26px;overflow:hidden;position:relative;"
            f"background:linear-gradient(135deg,#020617,#0f172a);"
            f"border:1px solid rgba(148,163,184,.18);"
            f"box-shadow:0 30px 80px rgba(0,0,0,.45);margin-bottom:28px;'>"
            f"<img src='{TEAM_URI}' style='"
            f"width:100%;display:block;object-fit:contain;background:#020617;min-height:260px;'>"
            f"<div style='position:absolute;inset:0;"
            f"background:linear-gradient(0deg,rgba(2,6,23,.80) 0%,transparent 55%);'></div>"
            f"<div style='position:absolute;bottom:28px;left:32px;right:32px;z-index:2;'>"
            f"<div style='font-size:11px;font-weight:800;color:#38bdf8;letter-spacing:.12em;"
            f"text-transform:uppercase;margin-bottom:8px;'>Team Preluma &nbsp;&bull;&nbsp; Yunnan University</div>"
            f"<div style='font-size:26px;font-weight:900;color:#fff;line-height:1.2;"
            f"text-shadow:0 4px 20px rgba(0,0,0,.60);'>"
            f"Building a smarter pre-class learning experience together.</div>"
            f"</div></div>",
            unsafe_allow_html=True,
        )
    else:
        st.warning("Team photo missing: assets/team_preluma.jpg")

    # Member cards
    m1, m2, m3 = st.columns(3)
    members = [
        (m1, "#0ea5e9", "MAMUNUR RASHID",
         "Lead Developer · Architecture · Deployment",
         "Built the complete Preluma architecture -- streamlit_app.py, engine.py, llm.py, project_core.py, homework_core.py, auth.py. Designed every page, built the login system, 3-Mood AI, student/teacher project system, and deployed to Streamlit Cloud.",
         "streamlit_app.py · engine.py · llm.py · project_core.py · auth.py"),
        (m2, "#10b981", "MD FAHIM",
         "Quiz Logic · Algorithm Validation · Python Testing",
         "Wrote and validated the quiz grading function in homework_core.py, tested all manual algorithm outputs in algorithms_core.py, contributed session state handling for the interaction flow, and validated the MCQ fix (no pre-selected options).",
         "homework_core.py · algorithms_core.py · teacher.py"),
        (m3, "#8b5cf6", "MD JIARUL ISLAM",
         "Topic Data · Data Quality & Testing · Storage",
         "Built and maintained all 29 topic packs in topics.py, contributed to the Wikipedia data pipeline in wiki_fetcher.py, and built data_quality.py -- automated unit tests for topic field validation, CSV schema integrity, duplicate detection, and homework/project data checks with nanosecond timing.",
         "topics.py · wiki_fetcher.py · storage_core.py · data_quality.py"),
    ]
    for col, color, name, role, desc, files in members:
        col.markdown(
            f"<div style='background:linear-gradient(145deg,rgba(15,23,42,.94),rgba(8,14,26,.98));"
            f"border:1px solid rgba(148,163,184,.09);border-top:3px solid {color};"
            f"border-radius:20px;padding:22px 18px;height:100%;'>"
            f"<div style='font-size:10px;font-weight:800;color:{color};letter-spacing:.10em;"
            f"text-transform:uppercase;margin-bottom:10px;'>{role}</div>"
            f"<div style='font-size:17px;font-weight:900;color:#f8fafc;margin-bottom:10px;'>{name}</div>"
            f"<div style='font-size:13px;color:#64748b;line-height:1.65;margin-bottom:12px;'>{desc}</div>"
            f"<div style='background:rgba(0,0,0,.30);border-radius:8px;padding:8px 12px;"
            f"border-left:3px solid {color}40;'>"
            f"<div style='font-size:9px;font-weight:800;color:{color};letter-spacing:.10em;"
            f"text-transform:uppercase;margin-bottom:4px;'>Python files</div>"
            f"<div style='font-size:11px;color:#64748b;font-family:monospace;'>{files}</div>"
            f"</div></div>",
            unsafe_allow_html=True,
        )

    st.markdown("<div style='height:24px'></div>", unsafe_allow_html=True)

    # Work division table
    st.markdown(
        "<div style='font-size:13px;font-weight:700;color:#475569;letter-spacing:.10em;"
        "text-transform:uppercase;margin-bottom:12px;'>Contribution Breakdown</div>",
        unsafe_allow_html=True,
    )
    st.dataframe([
        {
            "Member": "MAMUNUR RASHID",
            "Role": "Lead developer -- full architecture, AI integration, login system, UI design, deployment",
        },
        {
            "Member": "MD FAHIM",
            "Role": "Quiz & algorithm validation, session state handling, Python testing",
        },
        {
            "Member": "MD JIARUL ISLAM",
            "Role": "Topic data engineering, Wikipedia pipeline, CSV storage, data quality & testing",
        },
    ], use_container_width=True, hide_index=True)


def demo_guide():
    page_intro(
        "demo",
        "Presentation walkthrough",
        "Demo Guide",
        "A focused presentation sequence for showing the problem, student flow, algorithms, AI support, and teacher value.",
    )

    steps = [
        ("Open Preluma & Log In", "Show the login page. Log in as a student (STUDENT role) and then as a teacher (TEACHER role) to demonstrate role-based access control. Say: HMAC-signed session token -- survives browser refresh with zero network calls."),
        ("Show the Problem", "Students sit in lectures without preparation -- passive learning, low retention, bad questions. Preluma's 5-step mission solves this before class."),
        ("Student Mission -- Brain Brief", "Select Machine Learning, click Start Mission. Show Brain Brief: all key concepts explained, not just one -- 2-column layout, concept tabs."),
        ("Quiz + Mistake Clinic", "Take the quiz -- each question tests a different skill. Show MCQ with no pre-selected option (fixed bug). Every wrong answer gets a clear correction with reasoning."),
        ("Mock Test", "Show the mock test -- timed, full topic coverage, final readiness score with grade."),
        ("Ask Preluma AI -- 3 Moods", "Go to Ask Preluma AI. Switch between Normal Mode, Coach Mode, and Roast Mode -- show how the same answer changes tone completely. Ask the same question in all three."),
        ("Student Profile + Projects", "Open My Profile -- show rank badge, progress bars, homework stats. Open Class Projects -- create a personal project, toggle In Progress → Complete, upload a file. Show category folders (Documents, Presentations, Images)."),
        ("My Homework", "Open My Homework -- submit answers, show instant AI grading and mistake capture per question."),
        ("Teacher Side -- Homework Center", "Log in as teacher. Open Homework Center -- create a homework assignment, set questions and due date. Open Class Dashboard -- show class readiness chart and weak concept analysis."),
        ("Teacher Side -- Project Center", "Open Project Center -- create a class project, upload a brief. Open Student Projects tab -- show all completed student personal projects grouped by student with download."),
        ("Teacher Studio -- Algorithms", "Open Teacher Studio -- show Merge Sort O(n log n) ranking with nanosecond timing, Binary Search O(log n), CSV persistence proof, and audit log written to result.txt."),
        ("Evidence Board -- Live Tests", "Open Evidence Board. Click 'Run All Checks Now' -- show live data quality report: 29 topics validated, CSV schema checks, duplicate detection. All green."),
        ("Professor Defense", "Show the 8-point rubric -- real problem, Python solution, algorithm proof, data persistence, AI integration, teacher value, testing, future product."),
    ]
    for i, (title, desc) in enumerate(steps, 1):
        st.markdown(f"""<div class='card-glass' style='margin:6px 0;display:flex;gap:16px;align-items:flex-start;'>
          <div style='min-width:28px;height:28px;border-radius:50%;background:rgba(56,189,248,.15);border:1px solid rgba(56,189,248,.25);display:flex;align-items:center;justify-content:center;color:#38bdf8;font-size:12px;font-weight:800;flex-shrink:0;'>{i}</div>
          <div><div style='font-size:14px;font-weight:700;color:#f1f5f9;'>{title}</div><div style='font-size:13px;color:#94a3b8;margin-top:4px;'>{desc}</div></div>
        </div>""", unsafe_allow_html=True)

    st.success("Final line: Preluma does not replace teachers. It prepares students to understand teachers better.")


def roadmap():
    page_intro(
        "roadmap",
        "Product vision",
        "Future Roadmap",
        "Where Preluma goes next -- from prototype to real product.",
    )

    st.dataframe(pd.DataFrame({
        "Phase":      ["V40 -- Delivered","Next: V41","AI Upgrade","Real Product"],
        "Goal":       [
            "Login system, HMAC sessions, Student Profile, 3-Mood AI, Homework, Class Projects, Data Quality tests",
            "RAG: upload course PDF → retrieval → cited AI answers",
            "Weakness AI -- auto-detects weak concepts and generates targeted exercises",
            "Mobile app + real-time class codes + multi-teacher support",
        ],
        "Technology": [
            "Python + Streamlit + Supabase + Claude/Groq/Gemini + HMAC",
            "Embeddings + vector store + LLM",
            "LLM + student mistake history + adaptive quiz generation",
            "API backend + React Native + WebSockets",
        ],
        "Status":     ["✅ Live now","Next semester","Future","Long-term"],
    }), use_container_width=True)
    st.code(
        "V40 Now:  Python + Streamlit + Supabase + Wikipedia + Claude/Groq/Gemini\n"
        "          + HMAC Login + Homework + Projects + Data Quality Tests\n"
        "Next:     Upload course PDF → RAG retrieval → cited answers\n"
        "Later:    Adaptive weakness detection → auto-generated exercises\n"
        "Future:   Mobile app + teacher dashboard + real-time class codes",
        language="text",
    )

"""Student Mission: the guided 5-step pre-class flow (brief → examples → practice → mock test → overview)."""

from __future__ import annotations

import json

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

from components import progress_hooks

from components.ui_components import page_intro
from components.ui_components import progress_bar
from engine import build_brain_brief
from engine import build_pack
from engine import grade
from engine import make_questions
from engine import tutor_sections
from services.ai_service import active_provider as _provider
from services.mission_history_service import append_student_row
from services.mission_history_service import next_record_id
from services.mission_history_service import timestamp
from teacher import build_teacher_dataframe
from teacher import class_average_readiness
from topics import TOPIC_OPTIONS
from wiki_fetcher import smart_answer_from_pack

def mission_control():
    st.markdown("""
    <style>
    .mc-banner {
        background: linear-gradient(135deg, rgba(14,165,233,.10) 0%, rgba(99,102,241,.08) 100%);
        border: 1px solid rgba(56,189,248,.16);
        border-radius: 24px; padding: 28px 32px; margin-bottom: 28px;
        position: relative; overflow: hidden;
    }
    .mc-banner-glow {
        position: absolute; right: -60px; top: -60px;
        width: 200px; height: 200px; border-radius: 50%;
        background: radial-gradient(circle, rgba(99,102,241,.22) 0%, transparent 70%);
    }
    .mc-banner-title {
        font-size: 26px; font-weight: 900; color: #f1f5f9;
        margin-bottom: 8px; letter-spacing: -.03em;
    }
    .mc-banner-title span { color: #38bdf8; }
    .mc-banner-sub {
        font-size: 14px; color: #64748b; line-height: 1.60;
    }
    .mc-checklist {
        display: flex; flex-wrap: wrap; gap: 8px; margin-top: 14px;
    }
    .mc-check {
        background: rgba(52,211,153,.08); border: 1px solid rgba(52,211,153,.20);
        border-radius: 20px; padding: 4px 12px;
        font-size: 12px; color: #34d399; font-weight: 600;
    }
    </style>
    <div class="mc-banner">
        <div class="mc-banner-glow"></div>
        <div class="mc-banner-title">Mission Control &nbsp;<span>GO</span></div>
        <div class="mc-banner-sub">
            Set your topic, choose how deep you want to go, and let Preluma AI build
            your complete pre-class learning mission in seconds.
        </div>
        <div class="mc-checklist">
            <span class="mc-check">AI Brain Brief</span>
            <span class="mc-check">All Concepts in Tabs</span>
            <span class="mc-check">Quiz + Skill Check</span>
            <span class="mc-check">Mistake Clinic</span>
            <span class="mc-check">UltraTutor Answers</span>
            <span class="mc-check">Smart Class Questions</span>
        </div>
    </div>
    """, unsafe_allow_html=True)

    preset = st.selectbox("Demo preset", ["Manual Input","AI Class Demo","Python Exam Demo","Statistics Viva Demo"], index=0)
    preset_data = {
        "AI Class Demo":        ("Amir",  "Neural Network",      "Tomorrow 9 AM", "Coach Mode",  "Deep Understanding"),
        "Python Exam Demo":     ("Jia",   "Python Programming",  "Tomorrow 9 AM", "Normal Mode", "Exam/Viva Mode"),
        "Statistics Viva Demo": ("Nadia", "Statistics",          "Tomorrow 9 AM", "Coach Mode",  "Exam/Viva Mode"),
    }
    ds, dt, dtime, dp, dm = preset_data.get(preset, (
        st.session_state.student, st.session_state.topic, "Tomorrow 9 AM", st.session_state.persona, "Fast Review"))

    st.markdown("""
    <style>
    /* Mission form -- study environment feel */
    div[data-testid="stForm"] {
        background: linear-gradient(145deg, rgba(10,18,38,.96), rgba(6,12,26,.98));
        border: 1px solid rgba(56,189,248,.14);
        border-radius: 24px; padding: 28px 28px 20px; margin-top: 4px;
        box-shadow: 0 8px 40px rgba(0,0,0,.40), inset 0 1px 0 rgba(255,255,255,.04);
    }
    div[data-testid="stTextInput"] input,
    div[data-testid="stSelectbox"] > div {
        background: rgba(15,23,42,.80) !important;
        border: 1px solid rgba(56,189,248,.18) !important;
        border-radius: 12px !important; color: #e2e8f0 !important;
    }
    div[data-testid="stFormSubmitButton"] button {
        background: linear-gradient(135deg, #0ea5e9 0%, #6366f1 100%) !important;
        border: none !important; border-radius: 14px !important;
        font-weight: 800 !important; font-size: 16px !important;
        padding: 14px !important; letter-spacing: .02em !important;
        box-shadow: 0 8px 28px rgba(99,102,241,.38) !important;
        transition: transform .15s !important;
    }
    .mc-section-label {
        font-size: 10px; font-weight: 800; color: #38bdf8;
        letter-spacing: .10em; text-transform: uppercase;
        margin-bottom: 10px; margin-top: 4px;
    }
    </style>
    """, unsafe_allow_html=True)

    with st.form("mission_form", border=False):
        c1, c2, c3 = st.columns([1.4, 1, 0.9])
        with c1:
            st.markdown("<div class='mc-section-label'>Your details</div>", unsafe_allow_html=True)
            student      = st.text_input("Your name", value=ds, placeholder="Enter your name")
            topic_choice = st.selectbox("Lecture topic", TOPIC_OPTIONS,
                index=TOPIC_OPTIONS.index(dt) if dt in TOPIC_OPTIONS else 0)
            topic = st.text_input("Custom topic", placeholder="e.g. Reinforcement Learning") \
                    if topic_choice == "Custom Topic" else topic_choice
            lecture_time = st.text_input("Lecture time", value=dtime)
        with c2:
            st.markdown("<div class='mc-section-label'>Learning style</div>", unsafe_allow_html=True)
            persona       = st.radio("Tutor personality", ["Normal Mode","Coach Mode","Roast Mode"],
                captions=["Clear & direct","Warm & motivating","Funny pressure"],
                index=["Normal Mode","Coach Mode","Roast Mode"].index(dp) if dp in ["Normal Mode","Coach Mode","Roast Mode"] else 0)
            learning_mode = st.selectbox("Learning mode",["Fast Review","Deep Understanding","Exam/Viva Mode"],
                index=["Fast Review","Deep Understanding","Exam/Viva Mode"].index(dm) if dm in ["Fast Review","Deep Understanding","Exam/Viva Mode"] else 0)
        with c3:
            st.markdown("<div class='mc-section-label'>What you will get</div>", unsafe_allow_html=True)
            use_wiki = st.checkbox("Wikipedia real data", value=True)
            for item in [
                ("AI Brain Brief", "#38bdf8"),
                ("All concepts in tabs", "#818cf8"),
                ("Quiz + skill check", "#34d399"),
                ("Mistake clinic", "#f87171"),
                ("UltraTutor answers", "#fb923c"),
                ("Smart class questions", "#a78bfa"),
            ]:
                st.markdown(
                    f"<div style='display:flex;align-items:center;gap:8px;"
                    f"padding:4px 0;border-bottom:1px solid rgba(255,255,255,.04);'>"
                    f"<div style='width:6px;height:6px;border-radius:50%;"
                    f"background:{item[1]};flex-shrink:0;'></div>"
                    f"<span style='font-size:12px;color:#94a3b8;'>{item[0]}</span></div>",
                    unsafe_allow_html=True,
                )
        st.markdown("<div style='height:8px'></div>", unsafe_allow_html=True)
        start = st.form_submit_button("Start Pre-Class Mission", use_container_width=True)

    if start:
        if not topic or not topic.strip():
            st.warning("Please enter a topic first.")
            return
        with st.spinner("Building your AI-powered learning mission..."):
            pack = build_pack(topic, use_wikipedia=use_wiki)
            brief = build_brain_brief(pack)
            questions = make_questions(pack)
            try:
                from engine import build_enriched_class_questions
                class_qs = build_enriched_class_questions(pack)
            except Exception:
                class_qs = pack.get("class_questions", [])
        st.session_state.update({
            "student": student, "topic": topic, "persona": persona,
            "learning_mode": learning_mode, "use_wiki": use_wiki,
            "pack": pack, "brief": brief, "questions": questions,
            "class_questions": class_qs, "quiz_result": None,
            "latest_session": None, "tutor_history": [],
            "mission_started": True, "mission_step": 1,
            "practice_reflection": "",
        })
        st.rerun()


# Brain Brief
def brain_brief():
    if "brief" not in st.session_state: return
    b    = st.session_state.brief
    pack = st.session_state.pack

    st.markdown("""<div class='sec-head'>
      <div class='sec-icon' style='background:rgba(167,139,250,.12);'>01</div>
      <div><div class='sec-title'>Brain Brief</div><div class='sec-sub'>Your 2-minute primer before class</div></div>
    </div>""", unsafe_allow_html=True)

    mode = st.session_state.get("learning_mode","Fast Review")
    st.caption(f"Learning mode: {mode}")

    if b.get("study_tip"):
        st.markdown(f"<div class='ai-bar'><div class='ai-dot'></div><div class='ai-txt'>Before class: {b['study_tip']}</div></div>", unsafe_allow_html=True)

    c1, c2 = st.columns(2)
    with c1:
        st.markdown(f"""<div class='card-glass'><div class='albl lbl-blue'>What is it?</div><div class='atxt'>{b['tiny_answer']}</div></div>
        <div class='card-glass'><div class='albl lbl-purple'>Simply put</div><div class='atxt'>{b['simple']}</div></div>""", unsafe_allow_html=True)
    with c2:
        st.markdown(f"""<div class='card-glass'><div class='albl lbl-green'>Real-life example</div><div class='atxt'>{b['example']}</div></div>
        <div class='card-glass'><div class='albl lbl-red'>Common mistake</div><div class='atxt'>{b['misconception']}</div></div>""", unsafe_allow_html=True)

    all_concepts = b.get("all_concepts", {})
    if all_concepts:
        st.markdown("""<div class='sec-head' style='margin-top:1.5rem;'>
          <div class='sec-icon' style='background:rgba(251,191,36,.10);'>BB</div>
          <div><div class='sec-title'>All Key Concepts</div><div class='sec-sub'>Click each tab to explore in depth</div></div>
        </div>""", unsafe_allow_html=True)
        tabs = st.tabs([f"  {n.title()}  " for n in all_concepts])
        for tab, (cname, c) in zip(tabs, all_concepts.items()):
            with tab:
                col1, col2 = st.columns(2)
                with col1:
                    st.markdown(f"""<div class='concept-block'><div class='concept-block-title'>Definition</div><p>{c['definition']}</p></div>
                    <div class='concept-block'><div class='concept-block-title'>In simple words</div><p>{c['kid']}</p></div>""", unsafe_allow_html=True)
                with col2:
                    st.markdown(f"""<div class='concept-block'><div class='concept-block-title'>Real example</div><p>{c['example']}</p></div>
                    <div class='concept-block'><div class='concept-block-title'>Mistake · Exam tip</div><p><b>Mistake:</b> {c['mistake']}</p><p><b>Exam:</b> {c['exam']}</p></div>""", unsafe_allow_html=True)

    with st.expander("Key facts & source"):
        for fact in b.get("facts", []):
            st.markdown(f"<div style='padding:6px 0;color:#cbd5e1;font-size:14px;border-bottom:1px solid rgba(255,255,255,.05);'>→ {fact}</div>", unsafe_allow_html=True)
        if pack.get("source_url"):
            st.success("Real Wikipedia data used.")
            st.write(pack.get("source_url"))


# Quiz
def quiz():
    if "questions" not in st.session_state: return
    st.markdown("""<div class='sec-head'>
      <div class='sec-icon' style='background:rgba(34,211,238,.10);'>EX</div>
      <div><div class='sec-title'>Readiness Quiz</div><div class='sec-sub'>4 questions across 4 skill types -- find your weak spots</div></div>
    </div>""", unsafe_allow_html=True)

    progress_hooks.mark_quiz_started()
    skill_colors = {"Definition":"lbl-blue","Core Concept":"lbl-purple","Application":"lbl-green","Misconception":"lbl-orange"}
    with st.form("quiz_form", border=False):
        for i, q in enumerate(st.session_state.questions):
            sc = skill_colors.get(q["skill"],"lbl-blue")
            st.markdown(f"""<div class='card-glass' style='margin-bottom:4px;'>
              <div class='albl {sc}'>{q["skill"]}</div>
              <div style='font-size:15px;color:#f1f5f9;font-weight:600;margin-bottom:12px;'>{q["q"]}</div>
            </div>""", unsafe_allow_html=True)
            st.radio("", q["options"], key=f"quiz_{i}", index=None, label_visibility="collapsed")
            st.markdown("<div style='height:6px'></div>", unsafe_allow_html=True)
        submit = st.form_submit_button("Check My Readiness", use_container_width=True)

    if submit:
        answers = {i: st.session_state.get(f"quiz_{i}") or "" for i in range(len(st.session_state.questions))}
        result  = grade(st.session_state.questions, answers)
        st.session_state.quiz_result = result
        st.session_state.latest_session = {
            "Student": st.session_state.student, "Topic": st.session_state.pack["title"],
            "Readiness": result["pct"], "Weak Skill": result["weakest"],
        }
        st.session_state.score_history = st.session_state.get("score_history",[])
        st.session_state.score_history.append({"Attempt": len(st.session_state.score_history)+1,
            "Topic": st.session_state.pack["title"], "Score": result["pct"]})
        progress_hooks.record_mission(result, st.session_state.pack["title"])
        # Persist to CSV
        append_student_row({
            "Record ID": next_record_id(), "Student": st.session_state.student,
            "Topic": st.session_state.pack["title"], "Readiness": result["pct"],
            "Weak Skill": result["weakest"], "Quiz Score": result["score"],
            "Quiz Total": result["total"], "Lecture Time": st.session_state.get("learning_mode","Fast Review"),
            "Learning Mode": st.session_state.get("learning_mode","Fast Review"), "Created At": timestamp(),
        })
        st.rerun()


# Result helpers
def _rc(pct: float):
    """Return (pill_css_class, score_color) based on percentage."""
    if pct >= 75:
        return "pill-g", "#34d399"
    if pct >= 50:
        return "pill-y", "#fbbf24"
    return "pill-r", "#f87171"


def _rl(pct: float) -> str:
    """Return a result label based on percentage."""
    if pct >= 75: return "Excellent"
    if pct >= 50: return "Good Effort"
    return "Needs Practice"


def result_section():
    result = st.session_state.get("quiz_result")
    if not result: return

    pct       = result["pct"]
    pill_cls, color = _rc(pct)
    label     = _rl(pct)

    st.markdown("""<div class='sec-head'>
      <div class='sec-icon' style='background:rgba(52,211,153,.10);'>QZ</div>
      <div><div class='sec-title'>Your Result</div><div class='sec-sub'>Score breakdown and skill analysis</div></div>
    </div>""", unsafe_allow_html=True)

    c1, c2, c3 = st.columns([1,1.6,1])
    with c1:
        st.markdown(f"""<div class='card-glass' style='text-align:center;padding:28px 16px;'>
          <div class='score-big' style='color:{color};'>{pct}%</div>
          <div class='score-lbl'>{result['score']}/{result['total']} correct</div>
          <div class='r-pill {pill_cls}'>{label}</div>
        </div>""", unsafe_allow_html=True)
    with c2:
        rows = build_teacher_dataframe(st.session_state.latest_session)
        avg  = class_average_readiness(rows)
        fig  = go.Figure()
        fig.add_bar(x=["You","Class Avg"], y=[pct, avg], marker_color=[color,"#818cf8"],
                    text=[f"{pct}%",f"{avg}%"], textposition="outside")
        fig.update_layout(height=240, margin=dict(l=10,r=10,t=10,b=10),
            plot_bgcolor="rgba(0,0,0,0)", paper_bgcolor="rgba(0,0,0,0)", font_color="#94a3b8",
            yaxis=dict(range=[0,110], gridcolor="rgba(255,255,255,.05)"),
            xaxis=dict(gridcolor="rgba(0,0,0,0)"))
        st.plotly_chart(fig, use_container_width=True)
    with c3:
        st.markdown(f"""<div class='card-glass' style='text-align:center;padding:28px 16px;'>
          <div style='font-size:12px;color:#64748b;font-weight:700;margin-bottom:8px;'>WEAKEST SKILL</div>
          <div style='font-size:18px;font-weight:800;color:#f87171;'>{result['weakest']}</div>
          <div style='font-size:12px;color:#475569;margin-top:8px;'>Focus area</div>
        </div>""", unsafe_allow_html=True)

    st.markdown("""<div class='sec-head' style='margin-top:1.5rem;'>
      <div class='sec-icon' style='background:rgba(248,113,113,.10);'>AN</div>
      <div><div class='sec-title'>Mistake Clinic</div><div class='sec-sub'>Every wrong answer explained clearly</div></div>
    </div>""", unsafe_allow_html=True)

    for i, d in enumerate(result["details"], 1):
        ok = d["correct"]
        with st.expander(f"{'[OK]' if ok else '[NO]'} Q{i}: {d['skill']} -- {'Correct' if ok else 'Review needed'}"):
            col1, col2 = st.columns(2)
            with col1:
                st.markdown(f"<div style='font-size:13px;color:#64748b;'>Your answer</div><div style='font-size:14px;color:{'#34d399' if ok else '#f87171'};font-weight:600;'>{d['chosen'] or 'No answer'}</div>", unsafe_allow_html=True)
            with col2:
                st.markdown(f"<div style='font-size:13px;color:#64748b;'>Correct answer</div><div style='font-size:14px;color:#34d399;font-weight:600;'>{d['answer']}</div>", unsafe_allow_html=True)
            st.markdown(f"<div style='margin-top:10px;font-size:14px;color:#cbd5e1;'>{d['why']}</div>", unsafe_allow_html=True)
            if not ok:
                st.info("Fix: read the definition → find one real example → say it in your own words.")

    history = st.session_state.get("score_history",[])
    if len(history) >= 2:
        df_h = pd.DataFrame(history)
        fig2 = px.line(df_h, x="Attempt", y="Score", markers=True, title="Your Readiness Trend", range_y=[0,100])
        fig2.update_traces(line_color="#38bdf8", marker_color="#7c3aed")
        fig2.update_layout(height=260, margin=dict(l=10,r=10,t=40,b=10),
            plot_bgcolor="rgba(0,0,0,0)", paper_bgcolor="rgba(0,0,0,0)", font_color="#94a3b8")
        st.plotly_chart(fig2, use_container_width=True)


# ─── Mood Selector ───────────────────────────────────────────────────────────
def _mood_selector():
    """3-button mood picker -- updates st.session_state.persona in place."""
    current = st.session_state.get("persona", "Normal Mode")

    MOODS = [
        ("😊", "Normal Mode",  "Clear & direct",    "#38bdf8", "rgba(56,189,248,.10)", "rgba(56,189,248,.28)"),
        ("🏋️", "Coach Mode",   "Warm & motivating", "#34d399", "rgba(52,211,153,.10)", "rgba(52,211,153,.28)"),
        ("🔥", "Roast Mode",   "Funny pressure",    "#f87171", "rgba(248,113,113,.10)", "rgba(248,113,113,.28)"),
    ]

    st.markdown("""
    <style>
    .mood-wrap { display:flex; gap:10px; margin:4px 0 14px; }
    .mood-card {
        flex:1; border-radius:14px; padding:12px 10px 10px;
        cursor:pointer; text-align:center;
        border:1.5px solid rgba(255,255,255,.07);
        transition:all .15s;
    }
    .mood-card.active { border-width:2px; }
    .mood-emoji { font-size:20px; line-height:1; margin-bottom:4px; }
    .mood-name  { font-size:12px; font-weight:800; letter-spacing:.04em; }
    .mood-desc  { font-size:10px; color:#64748b; margin-top:2px; }
    </style>""", unsafe_allow_html=True)

    cards_html = "<div class='mood-wrap'>"
    for emoji, name, desc, color, bg, border in MOODS:
        is_active = (current == name)
        active_cls = " active" if is_active else ""
        style = (
            f"background:{bg};border-color:{border};" if is_active
            else "background:rgba(15,23,42,.50);border-color:rgba(255,255,255,.07);"
        )
        _nc = color if is_active else "#94a3b8"
        cards_html += (
            f"<div class='mood-card{active_cls}' style='{style}'>"
            f"<div class='mood-emoji'>{emoji}</div>"
            f"<div class='mood-name' style='color:{_nc};'>{name}</div>"
            f"<div class='mood-desc'>{desc}</div>"
            f"</div>"
        )
    cards_html += "</div>"
    st.markdown(cards_html, unsafe_allow_html=True)

    cols = st.columns(3)
    changed = False
    for col, (emoji, name, desc, color, bg, border) in zip(cols, MOODS):
        is_active = (current == name)
        btn_type = "primary" if is_active else "secondary"
        if col.button(
            f"{'✓ ' if is_active else ''}{name}",
            key=f"_mood_btn_{name}",
            use_container_width=True,
            type=btn_type,
        ):
            st.session_state.persona = name
            changed = True
    if changed:
        st.rerun()


# Smart QnA + UltraTutor
def smart_qna():
    if "pack" not in st.session_state: return

    st.markdown("""<div class='sec-head'>
      <div class='sec-icon' style='background:rgba(99,102,241,.12);'>AI</div>
      <div><div class='sec-title'>UltraTutor</div><div class='sec-sub'>Ask anything -- get an answer matched exactly to how you asked</div></div>
    </div>""", unsafe_allow_html=True)

    provider = _provider()
    if provider != "none":
        st.markdown(f"<div class='ai-bar'><div class='ai-dot'></div><div class='ai-txt'>AI active: {provider} -- ask simply for simple answers, ask deeply for deep answers</div></div>", unsafe_allow_html=True)
    else:
        st.markdown("<div class='notice'>Running on local data. Set GEMINI_API_KEY in Streamlit secrets for AI answers.</div>", unsafe_allow_html=True)

    _mood_selector()
    persona = st.session_state.get("persona","Normal Mode")
    hints = {"Normal Mode":"e.g. What is overfitting?","Coach Mode":"e.g. I'm confused, help me understand","Roast Mode":"e.g. Why does everyone talk about neural networks?"}
    question = st.text_input("", placeholder=hints.get(persona,"Ask any question about this topic..."), key="tutor_q", label_visibility="collapsed")

    col1, col2, col3 = st.columns([2,2,1])
    with col1:
        ask_smart = st.button("Smart Answer (local)", use_container_width=True)
    with col2:
        ask_tutor = st.button("UltraTutor (AI)", use_container_width=True)
    with col3:
        if st.button("Clear", use_container_width=True):
            st.session_state.tutor_history = []; st.rerun()

    if ask_smart and question.strip():
        ans = smart_answer_from_pack(st.session_state.pack, question)
        st.session_state.tutor_history.append({"question": question, "type": "smart", "response": ans})
        st.rerun()

    if ask_tutor and question.strip():
        with st.spinner("Thinking..."):
            s = tutor_sections(st.session_state.pack, question, persona)
        st.session_state.tutor_history.append({"question": question, "type": "tutor", "response": s})
        st.rerun()

    for entry in reversed(st.session_state.get("tutor_history",[])):
        q = entry["question"]
        r = entry["response"]
        t = entry.get("type","tutor")

        if t == "smart":
            st.markdown(f"<div style='margin:16px 0 4px;font-size:16px;font-weight:800;color:#f1f5f9;'>Smart Answer <span style='font-size:12px;color:#475569;margin-left:10px;'>\"{q}\"</span></div>", unsafe_allow_html=True)
            c1, c2 = st.columns(2)
            c1.markdown(f"<div class='card-glass'><div class='albl lbl-blue'>Answer</div><div class='atxt'>{r.get('answer','')}</div></div>", unsafe_allow_html=True)
            c2.markdown(f"<div class='card-glass'><div class='albl lbl-green'>Simple version</div><div class='atxt'>{r.get('simple','')}</div></div>", unsafe_allow_html=True)
            st.markdown(f"<div class='card-glass'><div class='albl lbl-purple'>Example</div><div class='atxt'>{r.get('example','')}</div></div>", unsafe_allow_html=True)
        else:
            st.markdown(f"<div style='margin:16px 0 4px;font-size:16px;font-weight:800;color:#f1f5f9;'>{r.get('concept','')} <span style='font-size:12px;color:#475569;margin-left:10px;'>\"{q}\"</span></div>", unsafe_allow_html=True)
            parts = [("Tiny Answer","lbl-blue",r.get("tiny_answer","")),
                     ("Explain Simply","lbl-purple",r.get("explain_simply","")),
                     ("Real-Life Example","lbl-green",r.get("real_life_example","")),
                     ("Common Mistake","lbl-red",r.get("common_mistake","")),
                     ("Exam Angle","lbl-yellow",r.get("exam_angle",""))]
            c1, c2 = st.columns(2)
            for idx,(title,lbl,text) in enumerate(parts):
                if not text: continue
                (c1 if idx%2==0 else c2).markdown(f"<div class='card-glass'><div class='albl {lbl}'>{title}</div><div class='atxt'>{text}</div></div>", unsafe_allow_html=True)
        st.markdown("<hr style='border-color:rgba(255,255,255,.05);margin:10px 0;'>", unsafe_allow_html=True)


# Class Questions
def class_questions_and_download():
    if "pack" not in st.session_state: return
    st.markdown("""<div class='sec-head'>
      <div class='sec-icon' style='background:rgba(34,211,238,.10);'>QA</div>
      <div><div class='sec-title'>Smart Class Questions</div><div class='sec-sub'>Walk into class with questions that show you prepared</div></div>
    </div>""", unsafe_allow_html=True)

    class_qs = st.session_state.get("class_questions", st.session_state.pack.get("class_questions",[]))
    for i, q in enumerate(class_qs, 1):
        st.markdown(f"<div class='card-glass' style='margin:6px 0;'><span style='color:#38bdf8;font-weight:700;font-size:13px;'>Q{i}</span><span style='color:#e2e8f0;font-size:14px;margin-left:10px;'>{q}</span></div>", unsafe_allow_html=True)

    payload = {"student": st.session_state.student, "topic": st.session_state.pack["title"],
               "brief": st.session_state.brief, "class_questions": class_qs,
               "quiz_result": st.session_state.get("quiz_result"),
               "learning_mode": st.session_state.get("learning_mode","Fast Review")}
    st.download_button("Download Study Brief", data=json.dumps(payload, indent=2),
        file_name=f"preluma_{st.session_state.pack['title'].lower().replace(' ','_')}.json",
        mime="application/json", use_container_width=True)


# How it works
def how_it_works():
    st.markdown("""<div class='kpi-grid'>
      <div class='kpi-card'><div class='kpi-num'>29</div><div class='kpi-lbl'>Curated Topics</div></div>
      <div class='kpi-card'><div class='kpi-num'>4</div><div class='kpi-lbl'>Skill Checks</div></div>
      <div class='kpi-card'><div class='kpi-num'>AI</div><div class='kpi-lbl'>Smart Tutor</div></div>
      <div class='kpi-card'><div class='kpi-num'>CSV</div><div class='kpi-lbl'>Persistent Data</div></div>
    </div>
    <div class='flow-grid'>
      <div class='flow-card'><div class='flow-step'>Step 1</div><div class='flow-title'>Prime the brain</div><div class='flow-desc'>AI Brain Brief with all concepts in tabs before the lecture.</div></div>
      <div class='flow-card'><div class='flow-step'>Step 2</div><div class='flow-title'>Find weak spots</div><div class='flow-desc'>4-question quiz detects exactly which skill needs work.</div></div>
      <div class='flow-card'><div class='flow-step'>Step 3</div><div class='flow-title'>Ask better questions</div><div class='flow-desc'>Leave with AI-generated class questions and a readiness score.</div></div>
    </div>""", unsafe_allow_html=True)


# Student Mission
def _set_mission_step(step: int) -> None:
    st.session_state.mission_step = max(1, min(5, int(step)))
    st.rerun()


def _mission_navigation(previous_step: int | None, next_step: int | None, next_label: str = "Next") -> None:
    left, center, right = st.columns([1, 2, 1])
    with left:
        if previous_step is not None and st.button("← Previous", use_container_width=True):
            _set_mission_step(previous_step)
    with center:
        step = st.session_state.get("mission_step", 1)
        st.progress(step / 5, text=f"Learning mission: Step {step} of 5")
    with right:
        if next_step is not None and st.button(f"{next_label} →", use_container_width=True):
            _set_mission_step(next_step)


def mission_brain_brief_screen() -> None:
    brief    = st.session_state.brief
    pack     = st.session_state.pack
    persona  = st.session_state.get("persona", "Normal Mode")
    mode     = st.session_state.get("learning_mode", "Fast Review")

    tiny          = brief.get("tiny_answer", "")
    simple        = brief.get("simple", "")
    example       = brief.get("example", "")
    misconception = brief.get("misconception", "") or (pack.get("misconceptions") or [""])[0]
    title         = brief.get("title", pack.get("title", "this topic"))
    all_concepts  = brief.get("all_concepts", {}) or pack.get("concepts", {})
    practice_qs   = pack.get("class_questions", [])[:5]

    # ── Mode + Persona label bar ──────────────────────────────────────────────
    mode_icons    = {"Fast Review": "⚡", "Deep Understanding": "🔬", "Exam/Viva Mode": "📝"}
    persona_colors = {"Normal Mode": "#38bdf8", "Coach Mode": "#34d399", "Roast Mode": "#fb923c"}
    p_color = persona_colors.get(persona, "#64748b")
    st.markdown(
        f"<div style='display:flex;gap:10px;align-items:center;margin-bottom:14px;'>"
        f"<span style='font-size:11px;font-weight:800;color:#64748b;letter-spacing:.08em;text-transform:uppercase;'>"
        f"{mode_icons.get(mode,'📖')} {mode}</span>"
        f"<span style='font-size:11px;font-weight:800;color:{p_color};letter-spacing:.06em;text-transform:uppercase;'>"
        f"· {persona}</span></div>",
        unsafe_allow_html=True,
    )

    st.markdown("""<div class='sec-head'>
      <div class='sec-icon' style='background:rgba(99,102,241,.15);'>01</div>
      <div><div class='sec-title'>Step 1 · Understand the Big Idea</div>
      <div class='sec-sub'>A friendly foundation before examples and practice</div></div>
    </div>""", unsafe_allow_html=True)

    # ══════════════════════════════════════════════════════════════════════════
    # FAST REVIEW -- 2-3 lines max, core answer only
    # ══════════════════════════════════════════════════════════════════════════
    if mode == "Fast Review":
        if persona == "Coach Mode":
            st.markdown(
                f"<div class='card-glass' style='border-color:rgba(52,211,153,.35);'>"
                f"<div class='albl lbl-green'>🌟 Quick Take (Coach)</div>"
                f"<div class='atxt'>Alright, here's what you need to know before class: <b>{tiny}</b> "
                f"Picture it like this -- {simple} That's really the heart of it. You've got this!</div></div>",
                unsafe_allow_html=True,
            )
        elif persona == "Roast Mode":
            st.markdown(
                f"<div class='card-glass' style='border-color:rgba(251,146,60,.35);'>"
                f"<div class='albl' style='color:#fb923c;'>😏 Fast Mode (Roast)</div>"
                f"<div class='atxt'>Okay fine, you picked Fast Review -- classic. Here's all you need: "
                f"<b>{tiny}</b> In plain human language: {simple} "
                f"That's it. Yes, really. Stop overthinking it. 😂</div></div>",
                unsafe_allow_html=True,
            )
        else:  # Normal
            st.markdown(
                f"<div class='card-glass' style='border-color:rgba(99,102,241,.35);'>"
                f"<div class='albl lbl-blue'>Core Answer</div>"
                f"<div class='atxt'>{tiny}</div></div>"
                f"<div class='card-glass'>"
                f"<div class='albl lbl-purple'>In simple terms</div>"
                f"<div class='atxt'>{simple}</div></div>",
                unsafe_allow_html=True,
            )

    # ══════════════════════════════════════════════════════════════════════════
    # DEEP UNDERSTANDING -- 7-10 lines, A to Z
    # ══════════════════════════════════════════════════════════════════════════
    elif mode == "Deep Understanding":
        if persona == "Coach Mode":
            st.markdown(
                f"<div class='card-glass' style='border-color:rgba(52,211,153,.35);padding:20px 22px;'>"
                f"<div class='albl lbl-green'>🎓 Teacher's Full Explanation</div>"
                f"<div class='atxt' style='line-height:1.9;'>"
                f"Let me walk you through this step by step. <b>{tiny}</b><br><br>"
                f"To really understand it, think of it this way: {simple}<br><br>"
                f"Here's a real-life example that makes this click: <i>{example}</i><br><br>"
                f"Now, this is very important -- avoid this common trap: {misconception} "
                f"Don't fall into that trap. Keep that in mind and you'll be ahead of the class."
                f"</div></div>",
                unsafe_allow_html=True,
            )
            if all_concepts:
                with st.expander("🔬 Explore all key concepts (Coach style)"):
                    tabs = st.tabs([n.title() for n in all_concepts])
                    for tab, (n, c) in zip(tabs, all_concepts.items()):
                        with tab:
                            st.markdown(f"**{n.title()}** -- {c.get('kid', c.get('definition',''))}")
                            st.caption(f"Exam angle: {c.get('exam','')}")

        elif persona == "Roast Mode":
            st.markdown(
                f"<div class='card-glass' style='border-color:rgba(251,146,60,.35);padding:20px 22px;'>"
                f"<div class='albl' style='color:#fb923c;'>😤 Deep Mode Roast -- Buckle Up</div>"
                f"<div class='atxt' style='line-height:1.9;'>"
                f"Oh, Deep Understanding? Feeling ambitious today, are we? Fine. Here's everything, since apparently a summary isn't enough for you:<br><br>"
                f"<b>{tiny}</b> (Yes, that's it. No, it's not more complicated than that.)<br><br>"
                f"If that definition made zero sense, try this: {simple}<br><br>"
                f"Still confused? Here's the example your brain actually needs: <i>{example}</i><br><br>"
                f"And since someone always asks -- here's the classic blunder every semester: {misconception} "
                f"Every semester. Same mistake. Don't be that person. 😂"
                f"</div></div>",
                unsafe_allow_html=True,
            )
            if all_concepts:
                with st.expander("🔬 Deeper concepts (because apparently you want more 😏)"):
                    tabs = st.tabs([n.title() for n in all_concepts])
                    for tab, (n, c) in zip(tabs, all_concepts.items()):
                        with tab:
                            st.write(c.get("kid", c.get("definition", "")))
                            st.caption(f"Exam angle: {c.get('exam','')}")

        else:  # Normal
            st.markdown(
                f"<div class='card-glass' style='border-color:rgba(99,102,241,.35);'>"
                f"<div class='albl lbl-blue'>Definition</div><div class='atxt'>{tiny}</div></div>"
                f"<div class='card-glass'><div class='albl lbl-purple'>Simple explanation</div>"
                f"<div class='atxt'>{simple}</div></div>",
                unsafe_allow_html=True,
            )
            col1, col2 = st.columns(2)
            with col1:
                st.markdown(
                    f"<div class='card-glass' style='border-color:rgba(52,211,153,.25);'>"
                    f"<div class='albl lbl-green'>Real example</div><div class='atxt'>{example}</div></div>",
                    unsafe_allow_html=True,
                )
            with col2:
                st.markdown(
                    f"<div class='card-glass' style='border-color:rgba(248,113,113,.25);'>"
                    f"<div class='albl lbl-red'>Common mistake</div><div class='atxt'>{misconception}</div></div>",
                    unsafe_allow_html=True,
                )
            if all_concepts:
                with st.expander("🔬 Deep dive -- all key concepts"):
                    tabs = st.tabs([n.title() for n in all_concepts])
                    for tab, (n, c) in zip(tabs, all_concepts.items()):
                        with tab:
                            st.write(c.get("kid", c.get("definition", "")))
                            st.caption(f"Exam angle: {c.get('exam','')}")

    # ══════════════════════════════════════════════════════════════════════════
    # EXAM / VIVA MODE -- key concept + practice questions
    # ══════════════════════════════════════════════════════════════════════════
    else:  # Exam/Viva Mode
        if persona == "Coach Mode":
            st.markdown(
                f"<div class='card-glass' style='border-color:rgba(52,211,153,.35);padding:18px 22px;'>"
                f"<div class='albl lbl-green'>📝 Exam Prep -- Coach Style</div>"
                f"<div class='atxt' style='line-height:1.85;'>"
                f"For your exam, the single most important definition to memorize is: <b>{tiny}</b><br><br>"
                f"Understand it through this: {simple}<br><br>"
                f"Critical warning -- do not fall into this trap: {misconception} "
                f"Make sure you know the difference. You've prepared well -- trust yourself!"
                f"</div></div>",
                unsafe_allow_html=True,
            )
        elif persona == "Roast Mode":
            st.markdown(
                f"<div class='card-glass' style='border-color:rgba(251,146,60,.35);padding:18px 22px;'>"
                f"<div class='albl' style='color:#fb923c;'>😬 Exam Mode -- No More Excuses</div>"
                f"<div class='atxt' style='line-height:1.85;'>"
                f"Exam mode, huh? A little late to start studying, but here we are. "
                f"The ONLY definition you need: <b>{tiny}</b><br><br>"
                f"And please -- PLEASE -- avoid this classic mistake: {misconception} "
                f"That's worth marks you cannot afford to lose. 😅<br><br>"
                f"Now stop reading this and practice the questions below."
                f"</div></div>",
                unsafe_allow_html=True,
            )
        else:  # Normal
            st.markdown(
                f"<div class='card-glass' style='border-color:rgba(99,102,241,.35);'>"
                f"<div class='albl lbl-blue'>📝 Key Definition</div><div class='atxt'>{tiny}</div></div>"
                f"<div class='card-glass' style='border-color:rgba(248,113,113,.35);'>"
                f"<div class='albl lbl-red'>⚠️ Common Exam Mistake</div><div class='atxt'>{misconception}</div></div>",
                unsafe_allow_html=True,
            )

        # Practice questions (all personas)
        if practice_qs:
            st.markdown("#### 📋 Practice Questions")
            for i, q in enumerate(practice_qs, 1):
                q_text = q if isinstance(q, str) else q.get("question", str(q))
                st.markdown(
                    f"<div class='card-glass' style='padding:10px 16px;margin-bottom:6px;'>"
                    f"<span style='color:#64748b;font-size:11px;font-weight:700;'>Q{i}</span> "
                    f"<span style='color:#e2e8f0;font-size:13px;'>{q_text}</span></div>",
                    unsafe_allow_html=True,
                )

    if pack.get("source_url"):
        st.caption("Source-supported topic pack is active.")

    _mission_navigation(None, 2, "See a Real Example")


def mission_example_screen() -> None:
    brief    = st.session_state.brief
    pack     = st.session_state.pack
    persona  = st.session_state.get("persona", "Normal Mode")
    mode     = st.session_state.get("learning_mode", "Fast Review")

    st.markdown("""<div class='sec-head'>
      <div class='sec-icon' style='background:rgba(168,85,247,.15);'>02</div>
      <div><div class='sec-title'>Step 2 · See It in Real Life</div>
      <div class='sec-sub'>Turn theory into a picture you can remember</div></div>
    </div>""", unsafe_allow_html=True)

    example      = brief.get("example", "")
    misconception = brief.get("misconception", "")
    applications  = pack.get("applications", {})
    title         = pack.get("title", "this topic")

    # ── Persona-aware example card ────────────────────────────────────────────
    if persona == "Coach Mode":
        st.markdown(
            f"<div class='card-glass' style='border-color:rgba(52,211,153,.35);'>"
            f"<div class='albl lbl-green'>🌍 Real-World Picture (Coach)</div>"
            f"<div class='atxt'>Here is a brilliant real-world example that will make <b>{title}</b> stick in your memory -- "
            f"pay close attention to how the concept shows up in real life:<br><br>{example}</div></div>",
            unsafe_allow_html=True,
        )
    elif persona == "Roast Mode":
        st.markdown(
            f"<div class='card-glass' style='border-color:rgba(251,146,60,.35);'>"
            f"<div class='albl' style='color:#fb923c;'>😏 Oh, you need an example?</div>"
            f"<div class='atxt'>Fine. Since abstract concepts clearly aren't your thing yet, here's a real-life example "
            f"that even a distracted student can understand:<br><br>{example}<br><br>"
            f"Remember this. It WILL come up. 😂</div></div>",
            unsafe_allow_html=True,
        )
    else:  # Normal
        st.markdown(
            f"<div class='card-glass' style='border-color:rgba(168,85,247,.35);'>"
            f"<div class='albl lbl-purple'>Imagine this</div>"
            f"<div class='atxt'>{example}</div></div>",
            unsafe_allow_html=True,
        )

    # ── Persona-aware misconception card ─────────────────────────────────────
    if persona == "Coach Mode":
        st.markdown(
            f"<div class='card-glass'>"
            f"<div class='albl lbl-red'>⚠️ Watch Out -- Common Trap</div>"
            f"<div class='atxt'>Many students fall into this mistake, so I want you to be aware: {misconception} "
            f"Keep this in mind and you will already be ahead of most of your classmates.</div></div>",
            unsafe_allow_html=True,
        )
    elif persona == "Roast Mode":
        st.markdown(
            f"<div class='card-glass'>"
            f"<div class='albl lbl-red'>🚨 Do NOT be this person</div>"
            f"<div class='atxt'>{misconception} "
            f"Half the class makes this exact mistake every single exam. Don't be half the class. 😅</div></div>",
            unsafe_allow_html=True,
        )
    else:
        st.markdown(
            f"<div class='card-glass'>"
            f"<div class='albl lbl-red'>Do not confuse it with this</div>"
            f"<div class='atxt'>{misconception}</div></div>",
            unsafe_allow_html=True,
        )

    # ── Extra detail for Deep Understanding mode ──────────────────────────────
    if mode == "Deep Understanding":
        study_tip = brief.get("study_tip", "")
        if study_tip:
            st.markdown(
                f"<div class='card-glass' style='border-color:rgba(56,189,248,.25);'>"
                f"<div class='albl lbl-blue'>📚 Deep Dive -- Study Action</div>"
                f"<div class='atxt'>{study_tip}</div></div>",
                unsafe_allow_html=True,
            )

    # ── Topic-specific applications ───────────────────────────────────────────
    _generic_app_keys = {"class learning", "general", "general learning"}
    _real_apps = {k: v for k, v in applications.items()
                  if k.lower() not in _generic_app_keys
                  and "prepare before lectures" not in str(v).lower()
                  and "helps students" not in str(v).lower()}
    if _real_apps:
        st.markdown("#### Where this idea is useful")
        cols = st.columns(min(3, len(_real_apps)))
        for index, (name, value) in enumerate(_real_apps.items()):
            cols[index % len(cols)].markdown(
                f"<div class='concept-block'><div class='concept-block-title'>"
                f"{name.title()}</div><p>{value}</p></div>",
                unsafe_allow_html=True,
            )

    # ── Memory tip ────────────────────────────────────────────────────────────
    memory_tips = {
        "Normal Mode": "Memory trick: connect the definition to one vivid example before trying to memorize it.",
        "Coach Mode":  "Pro tip from your coach: picture yourself explaining this example to a friend. That's how you truly lock it in memory! 💪",
        "Roast Mode":  "Memory tip: if you can't explain it with a real example, you don't know it yet. Just saying. 😏",
    }
    st.info(memory_tips.get(persona, memory_tips["Normal Mode"]))
    _mission_navigation(1, 3, "Try It Yourself")


def mission_practice_screen() -> None:
    brief        = st.session_state.brief
    pack         = st.session_state.pack
    persona      = st.session_state.get("persona", "Normal Mode")
    mode         = st.session_state.get("learning_mode", "Fast Review")
    concept_name = pack.get("title") or brief.get("key_concept", "the topic")

    st.markdown("""<div class='sec-head'>
      <div class='sec-icon' style='background:rgba(245,158,11,.15);'>03</div>
      <div><div class='sec-title'>Step 3 · Practice the Idea</div>
      <div class='sec-sub'>Active thinking makes the idea stay in memory</div></div>
    </div>""", unsafe_allow_html=True)

    # ── Challenge text by persona + mode ─────────────────────────────────────
    if persona == "Coach Mode":
        if mode == "Exam/Viva Mode":
            challenge = (f"You are almost ready for class! Write a proper exam-style answer for <b>{concept_name}</b>. "
                         f"Include: definition → key mechanism → one real example. Pretend this is your actual viva.")
        elif mode == "Deep Understanding":
            challenge = (f"This is your moment to go deep. Explain <b>{concept_name}</b> in your own words -- "
                         f"don't just define it, explain WHY it works and HOW it connects to real life. I believe in you! 💪")
        else:
            challenge = (f"Now it is YOUR turn! Try to explain <b>{concept_name}</b> in your own words. "
                         f"Don't overthink it -- just write what you understood, then give one real example.")
        border, label = "rgba(52,211,153,.35)", "lbl-green"
        lbl_text = "🎯 Your Challenge (Coach)"
    elif persona == "Roast Mode":
        if mode == "Exam/Viva Mode":
            challenge = (f"Exam mode? Okay genius -- write a proper definition of <b>{concept_name}</b> with a real example, "
                         f"as if your professor is staring at you right now. No vague answers. No excuses. 😬")
        elif mode == "Deep Understanding":
            challenge = (f"Oh, Deep Understanding? So you actually want to LEARN this time? Impressive. "
                         f"Explain <b>{concept_name}</b> properly -- what it is, why it matters, and a real example. Let's see it. 🔥")
        else:
            challenge = (f"Okay genius, it is YOUR turn now. Let's see if you actually understood <b>{concept_name}</b>. "
                         f"Write an explanation in your own words and give me one real example. No copy-pasting. 😏")
        border, label = "rgba(251,146,60,.35)", ""
        lbl_text = "😤 Your Challenge"
    else:  # Normal
        if mode == "Exam/Viva Mode":
            challenge = (f"Write an exam-ready answer for <b>{concept_name}</b>: definition, "
                         f"how it works, and one concrete example you could use in a viva.")
        elif mode == "Deep Understanding":
            challenge = (f"Explain <b>{concept_name}</b> in depth -- what it is, why it matters, "
                         f"how it works, and give one real-world example that shows your understanding.")
        else:
            challenge = f"Explain <b>{concept_name}</b> in your own words, then give one example."
        border, label = "rgba(245,158,11,.35)", "lbl-yellow"
        lbl_text = "Your challenge"

    st.markdown(
        f"<div class='card-glass' style='border-color:{border};'>"
        f"<div class='albl {label}'>{lbl_text}</div>"
        f"<div class='atxt'>{challenge}</div></div>",
        unsafe_allow_html=True,
    )

    placeholders = {
        "Fast Review":       "Start with: In simple words, this means...",
        "Deep Understanding":"Start with: At its core, this topic is about... and it matters because...",
        "Exam/Viva Mode":    "Start with: The definition of this topic is... It works by...",
    }
    reflection = st.text_area(
        "Write your explanation",
        value=st.session_state.get("practice_reflection", ""),
        placeholder=placeholders.get(mode, "Start with: In simple words, this means..."),
        height=150,
    )
    st.session_state.practice_reflection = reflection

    col1, col2 = st.columns(2)
    with col1:
        if st.button("Show a gentle hint", use_container_width=True):
            if mode == "Exam/Viva Mode":
                st.info(f"Exam structure: (1) Define it precisely. (2) Explain the mechanism. (3) Give a concrete example. Core idea: {brief.get('tiny_answer', '')}")
            elif mode == "Deep Understanding":
                st.info(f"Deep structure: What is it → Why does it exist → How does it work → Real example. Core: {brief.get('simple', '')}")
            else:
                st.info(f"Pattern: meaning → why it matters → example. Core idea: {brief.get('simple', '')}")
    with col2:
        if st.button("Check my thinking", use_container_width=True):
            word_count = len(reflection.split())
            min_words = 20 if mode in ("Deep Understanding", "Exam/Viva Mode") else 8
            if word_count < min_words:
                if persona == "Roast Mode":
                    st.warning(f"That's it? {word_count} words? Add more -- include both the meaning and an example. 😒")
                else:
                    st.warning("Add a little more: include both the meaning and an example.")
            elif "example" not in reflection.casefold() and "like" not in reflection.casefold() and "e.g" not in reflection.casefold():
                if persona == "Coach Mode":
                    st.info("Great start! Just add a concrete example -- that is the part that will stick in your memory. 💪")
                else:
                    st.info('Good start. Add a phrase such as "For example..." to make your explanation stronger.')
            else:
                if persona == "Coach Mode":
                    st.success("Excellent work! You explained the idea AND connected it to a real example. That is exactly how you build lasting understanding! 🌟")
                elif persona == "Roast Mode":
                    st.success("Okay... not bad. You actually explained it AND gave an example. Respect. 😤✅")
                else:
                    st.success("Strong practice answer. You explained the idea and connected it to an example.")

    _mission_navigation(2, 4, "Take the Mock Test")


def _save_mission_quiz_result(result: dict) -> None:
    progress_hooks.record_mission(result, st.session_state.pack["title"])
    st.session_state.quiz_result = result
    st.session_state.latest_session = {
        "Student": st.session_state.student,
        "Topic": st.session_state.pack["title"],
        "Readiness": result["pct"],
        "Weak Skill": result["weakest"],
    }
    st.session_state.score_history = st.session_state.get("score_history", [])
    st.session_state.score_history.append({
        "Attempt": len(st.session_state.score_history) + 1,
        "Topic": st.session_state.pack["title"],
        "Score": result["pct"],
    })
    append_student_row({
        "Record ID": next_record_id(),
        "Student": st.session_state.student,
        "Topic": st.session_state.pack["title"],
        "Readiness": result["pct"],
        "Weak Skill": result["weakest"],
        "Quiz Score": result["score"],
        "Quiz Total": result["total"],
        "Lecture Time": "Pre-class mission",
        "Learning Mode": st.session_state.get("learning_mode", "Fast Review"),
        "Created At": timestamp(),
    })


def mission_mock_test_screen() -> None:
    """
    Render the Step 4 mock test screen with four multiple-choice questions.

    Questions are drawn from the randomised pool built by engine.make_questions()
    so each attempt produces a different set. The student selects one answer per
    question using radio buttons, then submits the full test at once. Results
    are graded immediately by engine.grade() and stored in session state so
    the results overview screen can display them without re-grading.

    A 'Try Again (New Questions)' button on the results screen calls this
    function again with a freshly randomised question set.
    """
    progress_hooks.mark_quiz_started()
    st.markdown("""
    <style>
    @keyframes slide-in {
        from { opacity: 0; transform: translateX(28px); }
        to   { opacity: 1; transform: translateX(0); }
    }
    .mock-card {
        animation: slide-in .35s cubic-bezier(.22,.61,.36,1) both;
        background: linear-gradient(145deg, rgba(15,23,42,.90), rgba(8,14,28,.95));
        border: 1px solid rgba(255,255,255,.09); border-radius: 24px;
        padding: 32px 28px; margin-bottom: 20px;
    }
    .mock-skill-tag {
        display: inline-block; padding: 5px 14px; border-radius: 30px;
        font-size: 11px; font-weight: 800; letter-spacing: .09em;
        text-transform: uppercase; margin-bottom: 18px;
        background: rgba(239,68,68,.14); color: #f87171;
        border: 1px solid rgba(239,68,68,.28);
    }
    .mock-question-text {
        font-size: 19px; font-weight: 700; color: #f1f5f9;
        line-height: 1.50; margin-bottom: 28px;
    }
    .mock-progress-dots {
        display: flex; gap: 8px; margin-bottom: 24px;
    }
    .mock-dot {
        width: 34px; height: 6px; border-radius: 4px;
        background: rgba(255,255,255,.10);
    }
    .mock-dot.done   { background: #34d399; }
    .mock-dot.active { background: #38bdf8; }
    .mock-counter {
        font-size: 12px; font-weight: 700; color: #475569;
        letter-spacing: .06em; text-transform: uppercase;
        margin-bottom: 10px;
    }
    </style>
    """, unsafe_allow_html=True)

    st.markdown("""<div class='sec-head'>
      <div class='sec-icon' style='background:rgba(239,68,68,.15);'>04</div>
      <div><div class='sec-title'>Step 4 · Mini Mock Test</div>
      <div class='sec-sub'>One question at a time -- think before you pick</div></div>
    </div>""", unsafe_allow_html=True)

    questions = st.session_state.questions
    total = len(questions)

    # Results screen
    if st.session_state.get("quiz_result"):
        result = st.session_state.quiz_result
        pct = result["pct"]
        color = "#34d399" if pct >= 75 else ("#f59e0b" if pct >= 50 else "#f87171")
        st.markdown(f"""
        <div style="
            background: linear-gradient(145deg,rgba(15,23,42,.90),rgba(8,14,28,.95));
            border: 1px solid {color}44; border-radius: 24px; padding: 32px 28px;
            text-align: center; margin-bottom: 24px;
        ">
            <div style="font-size:48px;font-weight:900;color:{color};margin-bottom:8px;">
                {pct}%
            </div>
            <div style="font-size:16px;color:#94a3b8;margin-bottom:4px;">
                {result["score"]} out of {result["total"]} correct
            </div>
            <div style="font-size:13px;color:#475569;margin-top:12px;">
                Weakest skill: <span style="color:#f87171;font-weight:700;">
                {result["weakest"]}</span>
            </div>
        </div>
        """, unsafe_allow_html=True)
        for index, detail in enumerate(result["details"], 1):
            ok = detail["correct"]
            with st.expander(
                f"{'✓' if ok else '✗'} Q{index} · {detail['skill']} · "
                f"{'Correct' if ok else 'Review needed'}"
            ):
                c1, c2 = st.columns(2)
                c1.markdown(f"**Your answer:** {detail['chosen'] or 'No answer'}")
                c2.markdown(f"**Correct:** {detail['answer']}")
                st.info(detail["why"])
        # Try Again button — generates completely new questions from the same pack
        st.markdown("<div style='height:8px'></div>", unsafe_allow_html=True)
        col_retry, col_next_ov = st.columns(2)
        with col_retry:
            if st.button("🔄 Try Again (New Questions)", use_container_width=True):
                # Regenerate questions with fresh randomisation
                from engine import make_questions as _mq
                st.session_state.questions = _mq(st.session_state.pack)
                st.session_state.quiz_result = None
                st.session_state._mock_q_index = 0
                for _k in [k for k in st.session_state if k.startswith("_saved_mock_ans_")]:
                    st.session_state.pop(_k, None)
                st.rerun()
        with col_next_ov:
            _mission_navigation(3, 5, "View Final Overview")
        return

    # One-question-at-a-time flow
    idx = st.session_state.get("_mock_q_index", 0)
    if idx >= total:
        idx = total - 1
    st.session_state._mock_q_index = idx

    q = questions[idx]
    skill_colors = {
        "Definition":    ("rgba(56,189,248,.14)",  "#38bdf8",  "rgba(56,189,248,.28)"),
        "Core Concept":  ("rgba(167,139,250,.14)", "#a78bfa",  "rgba(167,139,250,.28)"),
        "Application":   ("rgba(52,211,153,.14)",  "#34d399",  "rgba(52,211,153,.28)"),
        "Misconception": ("rgba(251,191,36,.14)",  "#fbbf24",  "rgba(251,191,36,.28)"),
    }
    bg, fg, border = skill_colors.get(q["skill"], ("rgba(239,68,68,.14)", "#f87171", "rgba(239,68,68,.28)"))

    # Progress dots
    dots_html = "<div class='mock-progress-dots'>"
    for i in range(total):
        cls = "done" if i < idx else ("active" if i == idx else "")
        dots_html += f"<div class='mock-dot {cls}'></div>"
    dots_html += "</div>"

    st.markdown(f"""
    <div class="mock-card">
        <div class="mock-counter">Question {idx + 1} of {total}</div>
        {dots_html}
        <div style="
            display:inline-block; padding:5px 14px; border-radius:30px;
            font-size:11px; font-weight:800; letter-spacing:.09em;
            text-transform:uppercase; margin-bottom:18px;
            background:{bg}; color:{fg}; border:1px solid {border};
        ">{q["skill"]}</div>
        <div class="mock-question-text">{q["q"]}</div>
    </div>
    """, unsafe_allow_html=True)

    answer_key = f"mock_ans_{idx}"
    # Restore previously saved answer (widget state is cleared when navigating away)
    _prev_saved = st.session_state.get(f"_saved_mock_ans_{idx}")
    _default_idx = q["options"].index(_prev_saved) if _prev_saved in q["options"] else None
    chosen = st.radio(
        "Choose your answer",
        q["options"],
        key=answer_key,
        index=_default_idx,
        label_visibility="collapsed",
    )

    is_last = idx == total - 1
    col_prev, col_next = st.columns([1, 3])

    with col_prev:
        if idx > 0 and st.button("← Back", use_container_width=True):
            st.session_state[f"_saved_mock_ans_{idx}"] = chosen  # save before leaving
            st.session_state._mock_q_index = idx - 1
            st.rerun()

    with col_next:
        label = "Submit Mock Test" if is_last else f"Next Question →"
        if st.button(label, use_container_width=True, type="primary"):
            st.session_state[f"_saved_mock_ans_{idx}"] = chosen  # save before leaving
            if not is_last:
                st.session_state._mock_q_index = idx + 1
                st.rerun()
            else:
                # Collect all saved answers and grade
                answers = {}
                for i in range(total):
                    answers[i] = st.session_state.get(f"_saved_mock_ans_{i}", "")
                result = grade(questions, answers)
                _save_mission_quiz_result(result)
                st.session_state._mock_q_index = 0
                st.rerun()

    _mission_navigation(3, None)


def mission_overview_screen() -> None:
    brief = st.session_state.brief
    result = st.session_state.get("quiz_result")
    class_questions = st.session_state.get("class_questions", [])
    score = result.get("pct", 0) if result else 0
    weak = result.get("weakest", "Not tested") if result else "Not tested"

    st.markdown("""<div class='sec-head'>
      <div class='sec-icon' style='background:rgba(16,185,129,.15);'>05</div>
      <div><div class='sec-title'>Step 5 · Your Learning Overview</div>
      <div class='sec-sub'>What you know, what to review, and what to ask in class</div></div>
    </div>""", unsafe_allow_html=True)

    c1, c2, c3 = st.columns(3)
    c1.metric("Readiness", f"{score}%")
    c2.metric("Weakest skill", weak)
    c3.metric("Mission status", "Completed")

    st.markdown(f"""
    <div class='card-glass' style='border-color:rgba(16,185,129,.35);'>
      <div class='albl lbl-green'>One-sentence summary</div>
      <div class='atxt'>{brief.get("tiny_answer", "")}</div>
    </div>
    <div class='card-glass'>
      <div class='albl lbl-yellow'>Your next study action</div>
      <div class='atxt'>Review <b>{weak}</b>, explain the topic once in your own words, and ask one question during class.</div>
    </div>
    """, unsafe_allow_html=True)

    class_questions = st.session_state.get("class_questions", [])
    if class_questions:
        st.markdown(
            "<div style='font-size:10px;font-weight:800;color:#38bdf8;letter-spacing:.10em;"
            "text-transform:uppercase;margin:20px 0 12px;'>"
            "3 questions to ask in your next class</div>",
            unsafe_allow_html=True,
        )
        for number, question in enumerate(class_questions[:3], 1):
            st.markdown(
                f"<div style='background:linear-gradient(135deg,rgba(56,189,248,.07),rgba(99,102,241,.05));"
                f"border:1px solid rgba(56,189,248,.18);border-radius:16px;"
                f"padding:16px 20px;margin-bottom:10px;display:flex;gap:14px;align-items:flex-start;'>"
                f"<div style='min-width:28px;height:28px;border-radius:50%;"
                f"background:rgba(56,189,248,.15);border:1px solid rgba(56,189,248,.30);"
                f"display:flex;align-items:center;justify-content:center;"
                f"font-size:12px;font-weight:900;color:#38bdf8;flex-shrink:0;'>{number}</div>"
                f"<div style='font-size:14px;color:#cbd5e1;line-height:1.60;'>{question}</div>"
                f"</div>",
                unsafe_allow_html=True,
            )

    col1, col2, col3 = st.columns(3)
    with col1:
        if st.button("← Review Practice", use_container_width=True):
            _set_mission_step(3)
    with col2:
        if st.button("Ask Preluma AI", use_container_width=True):
            st.session_state.ai_context_note = (
                f"Current topic: {st.session_state.pack['title']}. "
                f"Student readiness: {score}%. Weak skill: {weak}."
            )
            st.session_state.force_page_ai = True
            st.info('Open "Ask Preluma AI" from the sidebar. Your topic context is ready.')
    with col3:
        if st.button("Start a New Mission", use_container_width=True):
            for key in ["pack", "brief", "questions", "quiz_result", "class_questions"]:
                st.session_state.pop(key, None)
            # Clear saved mock test answers
            for _k in [k for k in st.session_state if k.startswith("_saved_mock_ans_")]:
                st.session_state.pop(_k, None)
            st.session_state.mission_started = False
            st.session_state.mission_step = 0
            st.rerun()


def student_mission(presentation):
    """
    Render the student topic mission shell and topic selection form.

    A mission is a five-step guided learning sequence:
      Step 1 — Brain Brief: key definitions and facts from the content pack.
      Step 2 — Example Screen: a worked example connecting theory to practice.
      Step 3 — Practice Screen: an open reflection prompt with AI feedback.
      Step 4 — Mock Test: four randomised multiple-choice questions.
      Step 5 — Results Overview: score, weak skill, and next steps.

    This function handles the pre-mission topic selection screen. Once the
    student submits a topic, the content pack is built and the five-step
    mission screens are rendered by the dedicated mission_*_screen() functions.
    """
    if not st.session_state.get("mission_started") or "pack" not in st.session_state:
        page_intro(
            "ai",
            "Pre-class learning mission",
            "Student Mission",
            "Choose your topic, set your goal, and let Preluma guide you through a 5-step AI-powered preparation.",
        )

        st.markdown("""
        <div style='background:linear-gradient(135deg,rgba(14,165,233,.07),rgba(99,102,241,.07));
            border:1px solid rgba(99,102,241,.18); border-radius:18px;
            padding:18px 22px; margin:-4px 0 18px; line-height:1.85;'>
          <div style='font-size:11px;font-weight:800;color:#818cf8;letter-spacing:.10em;
              text-transform:uppercase;margin-bottom:10px;'>How the Mission Works</div>
          <div style='display:flex;flex-direction:column;gap:7px;'>
            <div style='font-size:13px;color:#cbd5e1;'>
              <span style='color:#38bdf8;font-weight:700;'>① Brain Brief</span>
              -- AI generates a 2-minute primer on every key concept so you walk into class already primed.
            </div>
            <div style='font-size:13px;color:#cbd5e1;'>
              <span style='color:#34d399;font-weight:700;'>② Examples</span>
              -- Real-world examples for each concept, grouped by topic tab, so theory connects to life.
            </div>
            <div style='font-size:13px;color:#cbd5e1;'>
              <span style='color:#a78bfa;font-weight:700;'>③ Quiz + Skill Check</span>
              -- Readiness quiz with instant scoring, weak-skill detection, and a UltraTutor for follow-up.
            </div>
            <div style='font-size:13px;color:#cbd5e1;'>
              <span style='color:#fb923c;font-weight:700;'>④ Mock Test</span>
              -- Timed question-by-question exam simulation with per-answer feedback and a final score.
            </div>
            <div style='font-size:13px;color:#cbd5e1;'>
              <span style='color:#f87171;font-weight:700;'>⑤ Class Ready</span>
              -- Smart class questions you can raise during the lecture, plus a full downloadable study brief.
            </div>
          </div>
        </div>
        """, unsafe_allow_html=True)

        mission_control()
        if presentation:
            how_it_works()
        return

    # Active mission -- back button + progress
    st.markdown("<div style='margin-top:12px;'></div>", unsafe_allow_html=True)
    if st.button("← Back to Mission Setup", key="mission_back_btn"):
        for k in ("mission_started", "pack", "brief", "quiz_result", "tutor_history",
                  "mission_step", "practice_reflection", "homework_result"):
            st.session_state.pop(k, None)
        st.rerun()
    st.markdown("<div style='margin-top:8px;'></div>", unsafe_allow_html=True)
    progress_bar()
    step = st.session_state.get("mission_step", 1)
    if step == 1:
        mission_brain_brief_screen()
    elif step == 2:
        mission_example_screen()
    elif step == 3:
        mission_practice_screen()
    elif step == 4:
        mission_mock_test_screen()
    else:
        mission_overview_screen()

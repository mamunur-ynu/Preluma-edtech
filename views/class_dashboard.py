"""Class Dashboard: homework results per student (teacher)."""

from __future__ import annotations


import streamlit as st

from auth import esc
from services.homework_service import update_homework
from services.user_service import is_admin_username, list_students

from components.ui_components import get_photo_src as _get_photo_src
from components.ui_components import page_intro
from services.homework_service import create_notification
from services.homework_service import hw_num
from services.homework_service import load_all_mistakes
from services.homework_service import load_homework
from services.homework_service import load_submissions
from views.profile import teacher_list

def class_dashboard_page():
    """
    Render the four-tab teacher class dashboard.

    Tab 1 — Send Announcement: compose and broadcast a message to all
      students or a specific group. Announcements appear as an orange
      banner on the student home page immediately after the next login.
    Tab 2 — Student Progress: charts and tables showing readiness scores,
      weak skill distribution, and topic coverage across the whole class.
    Tab 3 — Edit Homework: modify due dates, instructions, or difficulty
      on existing assignments, or remove outdated ones.
    Tab 4 — Student Lookup: search by name to view an individual student's
      mission history, homework scores, and identified weak concepts.
    """
    page_intro(
        "teacher",
        "Teacher · Command Centre",
        "Class Dashboard",
        "Announce, track progress, edit assignments, and look up individual students.",
    )

    # ── CSS shared across all tabs ──
    st.markdown("""
    <style>
    .db-card {
        background:linear-gradient(145deg,rgba(10,18,36,.97),rgba(6,12,26,.99));
        border:1px solid rgba(255,255,255,.07); border-radius:18px;
        padding:18px 22px; margin-bottom:14px;
    }
    .db-lbl {
        font-size:10px; font-weight:800; letter-spacing:.10em;
        text-transform:uppercase; margin-bottom:8px;
    }
    .db-lbl-blue  { color:#38bdf8; }
    .db-lbl-green { color:#34d399; }
    .db-lbl-amber { color:#f59e0b; }
    .db-lbl-purple{ color:#a78bfa; }
    .db-val { font-size:13px; color:#cbd5e1; }
    .db-name { font-size:15px; font-weight:700; color:#f1f5f9; margin-bottom:3px; }
    .db-sub  { font-size:11.5px; color:#a7bad2; }
    </style>
    """, unsafe_allow_html=True)

    _all_students = [{"Full Name": u.full_name, "Username": u.username} for u in list_students()]
    _student_names = [s.get("Full Name", s.get("Username","")) for s in _all_students]

    # Cache homework + submissions for the whole dashboard (reused across all tabs)
    if "_cached_hw" not in st.session_state:
        st.session_state["_cached_hw"] = load_homework()
    if "_cached_subs" not in st.session_state:
        st.session_state["_cached_subs"] = load_submissions()
    if "_cached_mistakes" not in st.session_state:
        st.session_state["_cached_mistakes"] = load_all_mistakes()
    _all_hw   = st.session_state["_cached_hw"]
    _all_subs = st.session_state["_cached_subs"]
    _all_mistakes_raw = st.session_state["_cached_mistakes"]

    # Group mistakes by student name for O(1) lookup
    _mistakes_by_student: dict = {}
    for _m in _all_mistakes_raw:
        _k = str(_m.get("Student", "")).strip().casefold()
        _mistakes_by_student.setdefault(_k, []).append(_m)

    tab1, tab2, tab3, tab4 = st.tabs(
        ["📢  Send Announcement", "📊  Student Progress", "✏️  Edit Homework", "🔍  Student Lookup"]
    )

    # ══════════════════════════════════════════════════════════════════
    # TAB 1 -- Send Announcement
    # ══════════════════════════════════════════════════════════════════
    with tab1:
        _ann_username = st.session_state.get("username", "").lower()
        _TLIST        = teacher_list()
        _is_admin_ann = is_admin_username(_ann_username)

        # ── If admin: pick which teacher sends this announcement ──────
        if _is_admin_ann:
            st.markdown(
                '<div style="font-size:11px;font-weight:800;color:#f59e0b;letter-spacing:.09em;'
                'text-transform:uppercase;margin-bottom:8px;">Admin: Select Announcing Teacher</div>',
                unsafe_allow_html=True,
            )
            _t_names = [t["name"] for t in _TLIST]
            _sel_idx = st.selectbox(
                "Send announcement as",
                range(len(_TLIST)),
                format_func=lambda i: f"{_TLIST[i]['name']}  ({_TLIST[i]['cn']})  -- {_TLIST[i]['course']}",
                key="ann_teacher_select",
                label_visibility="collapsed",
            )
            _ann_t = _TLIST[_sel_idx]
        else:
            # Logged-in teacher -- match by photo_key (username)
            _ann_t = next((t for t in _TLIST if t["photo_key"] == _ann_username), _TLIST[0])

        # ── Resolve teacher details ───────────────────────────────────
        _t_photo = _get_photo_src(_ann_t["photo_key"])
        _t_init  = "".join(w[0] for w in _ann_t["name"].split()[:2]).upper()

        # Build HTML pieces individually (avoids multiline f-string rendering bugs)
        if _t_photo:
            _av_html = (
                f'<img src="{_t_photo}" style="width:72px;height:72px;border-radius:16px;'
                f'object-fit:cover;border:2.5px solid rgba(56,189,248,.5);'
                f'box-shadow:0 4px 20px rgba(14,165,233,.3);">'
            )
        else:
            _av_html = (
                f'<div style="width:72px;height:72px;border-radius:16px;'
                f'background:linear-gradient(135deg,#0ea5e9 0%,#6366f1 100%);'
                f'display:flex;align-items:center;justify-content:center;'
                f'font-size:26px;font-weight:900;color:#fff;'
                f'box-shadow:0 4px 20px rgba(99,102,241,.3);">{_t_init}</div>'
            )
        _cn_html     = f'<span style="font-size:15px;color:#38bdf8;font-weight:600;margin-left:10px;">{_ann_t["cn"]}</span>'
        _badge_role  = f'<span style="font-size:11px;color:#94a3b8;background:rgba(255,255,255,.06);border:1px solid rgba(255,255,255,.1);border-radius:6px;padding:3px 9px;margin-right:6px;">{_ann_t["role"]}</span>'
        _badge_crs   = f'<span style="font-size:11px;color:#7dd3fc;background:rgba(56,189,248,.08);border:1px solid rgba(56,189,248,.18);border-radius:6px;padding:3px 9px;margin-right:6px;">📚 {_ann_t["course"]}</span>'
        _badge_mail  = f'<span style="font-size:11px;color:#a5b4fc;background:rgba(99,102,241,.08);border:1px solid rgba(99,102,241,.18);border-radius:6px;padding:3px 9px;">✉️ {_ann_t["email"]}</span>'

        st.markdown(
            '<div style="background:linear-gradient(135deg,rgba(14,165,233,.10) 0%,rgba(99,102,241,.07) 100%);'
            'border:1px solid rgba(56,189,248,.20);border-radius:22px;padding:22px 26px;'
            'margin-bottom:22px;display:flex;gap:20px;align-items:center;">'
            + _av_html +
            '<div style="flex:1;">'
            '<div style="font-size:10px;font-weight:800;color:#38bdf8;letter-spacing:.12em;'
            'text-transform:uppercase;margin-bottom:6px;">Sender · This Announcement</div>'
            f'<div style="font-size:22px;font-weight:900;color:#f1f5f9;line-height:1.1;">'
            f'{_ann_t["name"]}{_cn_html}</div>'
            f'<div style="margin-top:10px;display:flex;flex-wrap:wrap;gap:6px;">'
            f'{_badge_role}{_badge_crs}{_badge_mail}</div>'
            '</div></div>',
            unsafe_allow_html=True,
        )

        # ── Announcement form ─────────────────────────────────────────
        with st.form("announcement_form", border=False):
            ann_title = st.text_input(
                "Announcement title",
                placeholder="e.g. Class postponed to Thursday",
            )
            ann_msg = st.text_area(
                "Message",
                placeholder="Write your announcement here...",
                height=130,
            )
            _fc1, _fc2 = st.columns(2)
            ann_target = _fc1.radio(
                "Send to",
                ["All Students", "Specific Students"],
                horizontal=True,
            )
            ann_include_details = _fc2.checkbox(
                "Include contact details in notification",
                value=True,
                help="Students will see the teacher's course and email in their inbox.",
            )
            ann_specific = []
            if ann_target == "Specific Students":
                ann_specific = st.multiselect(
                    "Select students",
                    _student_names,
                    help="Hold Ctrl/Cmd to select multiple.",
                )
            ann_submit = st.form_submit_button("📢 Send Announcement", use_container_width=True)

        if ann_submit:
            if not ann_title.strip() or not ann_msg.strip():
                st.warning("Please fill in both title and message.")
            else:
                targets = _student_names if ann_target == "All Students" else ann_specific
                if not targets:
                    st.warning("Select at least one student.")
                else:
                    _body = ann_msg.strip()
                    if ann_include_details:
                        _body += f"\n\n-- {_ann_t['name']} | Course: {_ann_t['course']} | {_ann_t['email']}"
                    for name in targets:
                        create_notification(
                            student=name,
                            notification_type="Announcement",
                            title=ann_title.strip(),
                            message=_body,
                            reference_id=0,
                        )
                    st.success(
                        f"✅ Announcement sent to **{len(targets)} student(s)** from **{_ann_t['name']}**."
                    )

    # ══════════════════════════════════════════════════════════════════
    # TAB 2 -- Student Progress
    # ══════════════════════════════════════════════════════════════════
    with tab2:
        if not _student_names:
            st.info("No students registered yet.")
        else:
            # Build per-student summary using pre-cached data
            progress_rows = []
            for name in _student_names:
                student_subs = [s for s in _all_subs if s.get("Student") == name]
                scores = []
                for s in student_subs:
                    try:
                        scores.append(float(s.get("Percentage", 0)))
                    except Exception:  # nosec B110
                        pass
                mistakes = _mistakes_by_student.get(name.strip().casefold(), [])
                weak_concepts = list({m.get("Weak Concept","") for m in mistakes if m.get("Weak Concept")})
                progress_rows.append({
                    "Student":        name,
                    "Submissions":    len(student_subs),
                    "Avg Score":      f"{sum(scores)/len(scores):.0f}%" if scores else "--",
                    "Best Score":     f"{max(scores):.0f}%" if scores else "--",
                    "Weak Areas":     ", ".join(weak_concepts[:3]) if weak_concepts else "None",
                })

            # Summary metrics
            done_any = [r for r in progress_rows if r["Submissions"] > 0]
            m1,m2,m3,m4 = st.columns(4)
            m1.metric("Total Students", len(progress_rows))
            m2.metric("Active (submitted)", len(done_any))
            m3.metric("Not started", len(progress_rows) - len(done_any))
            m4.metric("Total Submissions", len(_all_subs))

            st.markdown("---")
            st.markdown(
                "<div class='db-lbl db-lbl-green' style='margin-bottom:10px;'>"
                "Per-student breakdown</div>",
                unsafe_allow_html=True,
            )
            for row in progress_rows:
                avg_color = "#34d399" if row["Avg Score"] not in ("--","0%") else "#a7bad2"
                st.markdown(f"""
                <div class="db-card" style="display:flex;justify-content:space-between;
                    align-items:center;flex-wrap:wrap;gap:12px;">
                  <div>
                    <div class="db-name">{esc(row['Student'])}</div>
                    <div class="db-sub">Weak areas: {esc(row['Weak Areas'])}</div>
                  </div>
                  <div style="display:flex;gap:24px;align-items:center;">
                    <div style="text-align:center;">
                      <div style="font-size:11px;color:#a7bad2;">Submissions</div>
                      <div style="font-size:18px;font-weight:800;color:#f1f5f9;">{row['Submissions']}</div>
                    </div>
                    <div style="text-align:center;">
                      <div style="font-size:11px;color:#a7bad2;">Avg Score</div>
                      <div style="font-size:18px;font-weight:800;color:{avg_color};">{row['Avg Score']}</div>
                    </div>
                    <div style="text-align:center;">
                      <div style="font-size:11px;color:#a7bad2;">Best</div>
                      <div style="font-size:18px;font-weight:800;color:#38bdf8;">{row['Best Score']}</div>
                    </div>
                  </div>
                </div>
                """, unsafe_allow_html=True)

    # ══════════════════════════════════════════════════════════════════
    # TAB 3 -- Edit Homework
    # ══════════════════════════════════════════════════════════════════
    with tab3:
        if not _all_hw:
            st.info("No homework published yet. Create one in Homework Center.")
        else:
            hw_labels = {
                f"#{hw_num(row)} · {row['Title']} (Due: {row['Due Date']})": row
                for row in _all_hw
            }
            selected_hw_label = st.selectbox(
                "Select homework to edit",
                list(hw_labels.keys()),
                key="edit_hw_select",
            )
            selected_hw = hw_labels[selected_hw_label]

            st.markdown(f"""
            <div class="db-card">
              <div class="db-lbl db-lbl-amber">Currently published</div>
              <div class="db-name">{esc(selected_hw.get('Title',''))}</div>
              <div class="db-sub">Topic: {esc(selected_hw.get('Topic',''))} &nbsp;|&nbsp;
              Assigned to: {esc(selected_hw.get('Assigned To',''))} &nbsp;|&nbsp;
              By: {esc(selected_hw.get('Created By',''))}</div>
            </div>
            """, unsafe_allow_html=True)

            with st.form("edit_hw_form", border=False):
                e1, e2 = st.columns(2)
                new_title = e1.text_input("Title", value=selected_hw.get("Title",""))
                new_topic = e2.text_input("Topic", value=selected_hw.get("Topic",""))
                new_instructions = st.text_area(
                    "Instructions",
                    value=selected_hw.get("Instructions",""),
                    height=100,
                )
                e3, e4 = st.columns(2)
                new_due = e3.text_input("Due date", value=selected_hw.get("Due Date",""))
                new_diff = e4.selectbox(
                    "Difficulty",
                    ["Beginner","Intermediate","Advanced"],
                    index=["Beginner","Intermediate","Advanced"].index(
                        selected_hw.get("Difficulty","Beginner")
                    ),
                )
                save_edit = st.form_submit_button("💾 Save Changes", use_container_width=True)

            if save_edit:
                changes = {"Title": new_title, "Topic": new_topic, "Instructions": new_instructions,
                           "Due Date": new_due, "Difficulty": new_diff}
                if update_homework(selected_hw.get("Homework ID"), changes):
                    st.success(f"✅ Homework #{hw_num(selected_hw)} updated.")
                    # Notify students of the change
                    for name in _student_names:
                        create_notification(
                            student=name,
                            notification_type="Update",
                            title=f"Homework Updated: {new_title.strip()}",
                            message=f"Due date is now {new_due.strip()}. Check your homework page.",
                            reference_id=selected_hw.get("Homework ID", 0),
                        )
                else:
                    st.error("Homework not found.")

    # ══════════════════════════════════════════════════════════════════
    # TAB 4 -- Student Lookup
    # ══════════════════════════════════════════════════════════════════
    with tab4:
        if not _student_names:
            st.info("No students registered yet.")
        else:
            lookup_name = st.selectbox(
                "Select student",
                _student_names,
                key="lookup_student_select",
            )

            all_subs_lookup = [s for s in _all_subs if s.get("Student") == lookup_name]
            mistakes_lookup = _mistakes_by_student.get(lookup_name.strip().casefold(), [])
            hw_done_ids     = {s.get("Homework ID") for s in all_subs_lookup}
            hw_pending      = [h for h in _all_hw if str(h.get("Homework ID")) not in hw_done_ids]

            scores = []
            for s in all_subs_lookup:
                try:
                    scores.append(float(s.get("Percentage", 0)))
                except Exception:  # nosec B110
                    pass

            # Summary strip
            s1,s2,s3,s4 = st.columns(4)
            s1.metric("Assignments Done",    len(all_subs_lookup))
            s2.metric("Pending",             len(hw_pending))
            s3.metric("Average Score",       f"{sum(scores)/len(scores):.0f}%" if scores else "--")
            s4.metric("Weak Concepts Found", len({m.get("Weak Concept") for m in mistakes_lookup if m.get("Weak Concept")}))

            st.markdown("---")

            # Submission history
            if all_subs_lookup:
                st.markdown(
                    "<div class='db-lbl db-lbl-purple' style='margin:10px 0 8px;'>"
                    "Submission history</div>",
                    unsafe_allow_html=True,
                )
                for sub in reversed(all_subs_lookup[-8:]):
                    pct  = sub.get("Percentage", "0")
                    try:   pct_f = float(pct)
                    except Exception: pct_f = 0
                    bar_color = "#34d399" if pct_f >= 70 else "#f59e0b" if pct_f >= 40 else "#f87171"
                    hw_title = next(
                        (h.get("Title","") for h in _all_hw
                         if str(h.get("Homework ID")) == str(sub.get("Homework ID"))),
                        f"Homework #{sub.get('HW Number', sub.get('Homework ID',''))}"
                    )
                    st.markdown(f"""
                    <div class="db-card" style="display:flex;justify-content:space-between;align-items:center;">
                      <div>
                        <div class="db-name">{esc(hw_title)}</div>
                        <div class="db-sub">Submitted: {esc(sub.get('Submitted At','')[:16])}</div>
                      </div>
                      <div style="font-size:22px;font-weight:900;color:{bar_color};">{esc(pct)}%</div>
                    </div>
                    """, unsafe_allow_html=True)
            else:
                st.info(f"{lookup_name} has not submitted any homework yet.")

            # Weak concepts
            if mistakes_lookup:
                st.markdown(
                    "<div class='db-lbl db-lbl-amber' style='margin:16px 0 8px;'>"
                    "Weak concepts (from wrong answers)</div>",
                    unsafe_allow_html=True,
                )
                weak_freq: dict[str, int] = {}
                for m in mistakes_lookup:
                    c = m.get("Weak Concept","")
                    if c: weak_freq[c] = weak_freq.get(c, 0) + 1
                for concept, count in sorted(weak_freq.items(), key=lambda x: -x[1])[:8]:
                    st.markdown(
                        f"<div class='db-card' style='display:flex;justify-content:space-between;'>"
                        f"<span class='db-val'>{esc(concept)}</span>"
                        f"<span style='color:#f87171;font-weight:700;'>{count}×</span></div>",
                        unsafe_allow_html=True,
                    )

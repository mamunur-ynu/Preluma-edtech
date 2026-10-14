"""Class projects and personal projects (student and teacher views, file uploads)."""

from __future__ import annotations

from pathlib import Path

import streamlit as st

from auth import esc
from components.ui_components import page_intro
from services import project_service as _pc

_ALLOWED_EXTS = {".pdf", ".ppt", ".pptx", ".doc", ".docx", ".txt", ".png", ".jpg", ".jpeg", ".zip"}


_MAX_FILE_MB   = 25


def _file_icon(fname: str) -> str:
    ext = Path(fname).suffix.lower()
    return {"pdf": "📄", "ppt": "📊", "pptx": "📊", "doc": "📝", "docx": "📝",
            "txt": "📋", "zip": "🗜️", "png": "🖼️", "jpg": "🖼️", "jpeg": "🖼️"}.get(ext.lstrip("."), "📎")


def _project_card(p: dict, badge: str = "", badge_color: str = "#38bdf8") -> None:
    """Render a compact project info card."""
    badge_html = (
        f"<span style='background:{badge_color}18;border:1px solid {badge_color}40;"
        f"color:{badge_color};font-size:10px;font-weight:800;letter-spacing:.06em;"
        f"padding:2px 9px;border-radius:20px;margin-left:8px;'>{esc(badge)}</span>"
    ) if badge else ""
    st.markdown(
        f"<div style='background:linear-gradient(145deg,rgba(10,18,38,.97),rgba(6,12,26,.99));"
        f"border:1px solid rgba(255,255,255,.07);border-radius:18px;padding:18px 20px 14px;'>"
        f"<div style='font-size:17px;font-weight:900;color:#f1f5f9;margin-bottom:4px;'>"
        f"{esc(p.get('Title',''))}{badge_html}</div>"
        f"<div style='font-size:13px;color:#94a3b8;line-height:1.65;margin-bottom:8px;'>"
        f"{esc(p.get('Description',''))}</div>"
        f"<div style='display:flex;gap:12px;flex-wrap:wrap;'>"
        f"<span style='font-size:11px;color:#64748b;'>📅 Due: <b style='color:#e2e8f0;'>"
        f"{esc(p.get('Due Date',''))}</b></span>"
        f"<span style='font-size:11px;color:#64748b;'>👤 By: <b style='color:#e2e8f0;'>"
        f"{esc(p.get('Created By',''))}</b></span>"
        f"<span style='font-size:11px;color:#64748b;'>🆔 <b style='color:#475569;'>"
        f"{esc(p.get('Project ID',''))}</b></span>"
        f"</div></div>",
        unsafe_allow_html=True,
    )


def _file_row(f: dict, dl_key: str, save_key: str) -> None:
    """Render one file row with a download button."""
    col_a, col_b = st.columns([5, 1])
    notes_disp = f.get("notes","") or ""
    notes_part = f" · <span style='color:#818cf8;font-style:italic;'>{esc(notes_disp)}</span>" if notes_disp else ""
    col_a.markdown(
        f"<div style='padding:9px 14px;background:rgba(15,23,42,.55);"
        f"border:1px solid rgba(255,255,255,.06);border-radius:11px;'>"
        f"<span style='font-size:13px;color:#e2e8f0;'>"
        f"{_file_icon(f.get('file_name',''))} <b>{esc(f.get('file_name',''))}</b></span>"
        f"<span style='font-size:11px;color:#475569;margin-left:10px;'>"
        f"{esc(f.get('created_at','')[:16])}{notes_part}</span></div>",
        unsafe_allow_html=True,
    )
    if col_b.button("⬇", key=dl_key, use_container_width=True):
        with st.spinner("Fetching..."):
            raw, fname, ftype = _pc.download_file(f["file_id"])
        if raw:
            col_b.download_button(
                "💾", data=raw, file_name=fname,
                mime=ftype or "application/octet-stream", key=save_key,
            )
        else:
            col_b.error("Failed")


def _file_category(fname: str) -> tuple[str, str]:
    """Return (category_label, accent_color) based on file extension."""
    ext = "." + fname.rsplit(".", 1)[-1].lower() if "." in fname else ""
    if ext in {".pdf", ".doc", ".docx", ".txt"}:
        return ("Documents", "#38bdf8")
    if ext in {".ppt", ".pptx"}:
        return ("Presentations", "#a78bfa")
    if ext in {".png", ".jpg", ".jpeg"}:
        return ("Images", "#fb923c")
    if ext in {".zip"}:
        return ("Archives", "#34d399")
    return ("Other", "#94a3b8")


def _render_file_folders(files: list[dict], key_prefix: str) -> None:
    """Clean minimal folder display -- grouped by file type."""
    if not files:
        return
    cats: dict[str, list] = {}
    cat_colors: dict[str, str] = {}
    for f in files:
        lbl, color = _file_category(f.get("file_name", ""))
        cats.setdefault(lbl, []).append(f)
        cat_colors[lbl] = color

    st.markdown("<div style='margin-top:14px;'>", unsafe_allow_html=True)
    global_idx = 0
    for cat_label, cat_files in cats.items():
        accent = cat_colors[cat_label]
        n = len(cat_files)
        # Clean section header -- label + count + thin rule
        st.markdown(
            f"<div style='display:flex;align-items:center;gap:10px;margin:14px 0 6px;'>"
            f"<span style='font-size:11px;font-weight:700;color:{accent};letter-spacing:.06em;'>"
            f"{cat_label}</span>"
            f"<span style='font-size:11px;color:#475569;'>-- {n} file{'s' if n>1 else ''}</span>"
            f"<div style='flex:1;height:1px;background:rgba(255,255,255,.07);'></div>"
            f"</div>",
            unsafe_allow_html=True,
        )
        for f in sorted(cat_files, key=lambda x: x.get("created_at", ""), reverse=True):
            _file_row(f, f"{key_prefix}_dl_{global_idx}", f"{key_prefix}_sv_{global_idx}")
            global_idx += 1
    st.markdown("</div>", unsafe_allow_html=True)


def _upload_panel(project_id: str, uploader: str, role: str, key_pfx: str) -> None:
    """Clean upload widget -- file picker + optional note + upload button."""
    _reset_n = st.session_state.get(f"_upn_{key_pfx}", 0)
    up = st.file_uploader(
        "Choose file (PDF, PPT, DOCX, ZIP, IMG)",
        type=[e.lstrip(".") for e in _ALLOWED_EXTS],
        key=f"{key_pfx}_up_{_reset_n}",
        accept_multiple_files=False,
        label_visibility="collapsed",
    )
    if up is not None:
        size_mb = up.size / (1024 * 1024)
        # File preview row
        st.markdown(
            f"<div style='display:flex;align-items:center;gap:10px;padding:10px 14px;"
            f"background:rgba(255,255,255,.04);border:1px solid rgba(255,255,255,.08);"
            f"border-radius:10px;margin:4px 0 10px;'>"
            f"<span style='font-size:20px;'>{_file_icon(up.name)}</span>"
            f"<div><div style='font-size:13px;font-weight:600;color:#e2e8f0;'>{esc(up.name)}</div>"
            f"<div style='font-size:11px;color:#64748b;'>{size_mb:.2f} MB</div></div>"
            f"</div>",
            unsafe_allow_html=True,
        )
        if size_mb > _MAX_FILE_MB:
            st.warning(f"File too large ({size_mb:.1f} MB). Max {_MAX_FILE_MB} MB.")
        else:
            notes_val = st.text_input("Note (optional)", key=f"{key_pfx}_notes",
                                      placeholder="e.g. Final version, Draft 2")
            if st.button(f"⬆  Upload", key=f"{key_pfx}_btn", type="primary",
                         use_container_width=True):
                with st.spinner(f"Uploading {up.name}..."):
                    ok, err_detail = _pc.upload_file(
                        project_id    = project_id,
                        uploader      = uploader,
                        uploader_role = role,
                        file_name     = up.name,
                        file_bytes    = up.getvalue(),
                        file_type     = up.type or "",
                        notes         = notes_val,
                    )
                if ok:
                    st.success(f"✓  {up.name} uploaded.")
                    st.session_state[f"_upn_{key_pfx}"] = _reset_n + 1
                    st.rerun()
                else:
                    st.error(f"✗  Upload failed: {err_detail}")


def student_project_page():
    """Student view -- My Projects (personal) + Class Projects (teacher-assigned)."""
    student  = st.session_state.get("student", "")
    username = st.session_state.get("username", "")
    me       = student or username

    page_intro(
        "student",
        "Your projects & class assignments",
        "Class Projects",
        "Manage your personal projects and submit work for teacher-assigned class projects.",
    )

    # ── Page-level CSS ───────────────────────────────────────────────
    st.markdown("""
    <style>
    /* Class project badge */
    .cp-badge {
        display:inline-block;padding:2px 10px;border-radius:20px;
        font-size:10px;font-weight:700;letter-spacing:.06em;
    }
    </style>
    """, unsafe_allow_html=True)

    tab_mine, tab_class = st.tabs(["📁 My Projects", "🏫 Class Projects"])

    # ════════════════════════════════════════════════════════════════
    # TAB 1 -- My Projects
    # ════════════════════════════════════════════════════════════════
    with tab_mine:

        # ── Create new project panel ─────────────────────────────
        st.markdown("""
        <div style='background:linear-gradient(135deg,rgba(99,102,241,.10),rgba(56,189,248,.07));
            border:1px solid rgba(99,102,241,.22);border-radius:18px;padding:18px 20px 6px;margin-bottom:14px;'>
          <div style='font-size:13px;font-weight:800;color:#818cf8;letter-spacing:.08em;
              text-transform:uppercase;margin-bottom:12px;'>➕ Create New Project</div>
        """, unsafe_allow_html=True)

        with st.form("create_personal_proj", border=False):
            np_title = st.text_input("Project title *", placeholder="e.g. Preluma AI Learning Platform")
            col_desc, col_side = st.columns([3, 2])
            with col_desc:
                np_desc = st.text_area("Description", height=90,
                    placeholder="What is this project about? What are you building or researching?")
            with col_side:
                np_status = st.radio(
                    "Visibility",
                    ["In Progress", "Complete"],
                    index=0,
                    help="In Progress = private (only you). Complete = teacher can view it.",
                )
                np_files = st.file_uploader(
                    f"Attach files now (optional)",
                    type=[e.lstrip(".") for e in _ALLOWED_EXTS],
                    accept_multiple_files=True,
                    key="np_init_files",
                )
            create_personal_btn = st.form_submit_button(
                "Create Project", type="primary", use_container_width=True)

        st.markdown("</div>", unsafe_allow_html=True)

        if create_personal_btn:
            if not np_title.strip():
                st.warning("Please enter a project title.")
            else:
                try:
                    new_pid = _pc.create_personal_project(np_title, np_desc, me, np_status)
                    if np_files:
                        failed_files = []
                        with st.spinner(f"Uploading {len(np_files)} file(s)..."):
                            for uf in np_files:
                                sz = uf.size / (1024 * 1024)
                                if sz > _MAX_FILE_MB:
                                    failed_files.append(f"{uf.name} (too large: {sz:.1f} MB)")
                                else:
                                    ok, err_msg = _pc.upload_file(
                                        project_id    = new_pid,
                                        uploader      = me,
                                        uploader_role = "student",
                                        file_name     = uf.name,
                                        file_bytes    = uf.getvalue(),
                                        file_type     = uf.type or "",
                                        notes         = "",
                                    )
                                    if not ok:
                                        failed_files.append(f"{uf.name} ({err_msg})")
                        if failed_files:
                            st.success("✓ Project created!")
                            for f in failed_files:
                                st.error(f"✗ Upload failed: {f}")
                        else:
                            st.success(f"✓ Project created! {len(np_files)} file(s) uploaded.")
                    else:
                        st.success("✓ Project created!")
                    st.rerun()
                except Exception as _e:
                    st.error(f"Error creating project: {_e}")

        # ── List existing personal projects ──────────────────────
        my_projects = _pc.load_personal_projects(me, include_in_progress=True)

        if not my_projects:
            st.markdown(
                "<div style='border:1px dashed rgba(167,139,250,.20);border-radius:16px;"
                "padding:28px;text-align:center;color:#64748b;margin-top:8px;'>"
                "You have no personal projects yet.<br>"
                "<span style='font-size:12px;'>Create one above -- start in progress, "
                "mark complete when ready to share with your teacher.</span></div>",
                unsafe_allow_html=True,
            )
        else:
            for mp in sorted(my_projects, key=lambda x: x.get("Created At", ""), reverse=True):
                mpid     = mp.get("Project ID", "")
                mstatus  = mp.get("Status", "In Progress")
                is_done  = mstatus == "Complete"
                s_color  = "#34d399" if is_done else "#fbbf24"
                desc_txt = mp.get("Description", "") or ""
                due_txt  = mp.get("Due Date", "") or ""
                created  = (mp.get("Created At", "") or "")[:10]
                title    = mp.get("Title", "Untitled")

                # Expander label: title + status suffix
                exp_label = f"{title}  ·  {mstatus}"

                with st.expander(exp_label, expanded=False):
                    # Status + meta row
                    meta_parts = [f"created {created}"]
                    if due_txt:
                        meta_parts.append(f"due {due_txt}")
                    st.markdown(
                        f"<div style='display:flex;align-items:center;gap:8px;margin-bottom:10px;'>"
                        f"<span style='width:7px;height:7px;border-radius:50%;"
                        f"background:{s_color};display:inline-block;flex-shrink:0;'></span>"
                        f"<span style='font-size:11px;color:{s_color};font-weight:700;"
                        f"letter-spacing:.05em;'>{mstatus.upper()}</span>"
                        f"<span style='font-size:11px;color:#475569;'>"
                        f"{'  ·  '.join(meta_parts)}</span></div>",
                        unsafe_allow_html=True,
                    )

                    if desc_txt:
                        st.markdown(
                            f"<p style='color:#94a3b8;font-size:13px;margin:0 0 14px;"
                            f"line-height:1.6;'>{desc_txt}</p>",
                            unsafe_allow_html=True,
                        )

                    # Files
                    mp_files = _pc.get_project_files(project_id=mpid, uploader=me)
                    if mp_files:
                        _render_file_folders(mp_files, f"mpf_{mpid}")

                    # Upload section
                    st.markdown(
                        "<div style='margin-top:14px;padding-top:12px;"
                        "border-top:1px solid rgba(255,255,255,.05);'>"
                        "<div style='font-size:10px;font-weight:700;color:#64748b;"
                        "letter-spacing:.08em;text-transform:uppercase;margin-bottom:8px;'>"
                        "Add File</div></div>",
                        unsafe_allow_html=True,
                    )
                    _upload_panel(mpid, me, "student", f"mp_{mpid}")

                    # Status toggle -- small, at bottom
                    st.markdown(
                        "<div style='margin-top:12px;padding-top:10px;"
                        "border-top:1px solid rgba(255,255,255,.04);'></div>",
                        unsafe_allow_html=True,
                    )
                    toggle_label = "mark complete" if not is_done else "move to in progress"
                    toggle_new   = "Complete" if not is_done else "In Progress"
                    _tc, _ = st.columns([2, 5])
                    if _tc.button(toggle_label, key=f"tog_{mpid}"):
                        _pc.update_project_status(mpid, toggle_new)
                        st.rerun()

    # ════════════════════════════════════════════════════════════════
    # TAB 2 -- Class Projects (teacher-assigned)
    # ════════════════════════════════════════════════════════════════
    with tab_class:
        class_projects = _pc.load_class_projects()

        if not class_projects:
            st.markdown(
                "<div style='background:rgba(56,189,248,.05);border:1px dashed rgba(56,189,248,.20);"
                "border-radius:16px;padding:28px;text-align:center;color:#64748b;'>"
                "No class projects yet.<br>"
                "<span style='font-size:12px;'>Your teacher will publish assignments here.</span></div>",
                unsafe_allow_html=True,
            )
        else:
            for p in class_projects:
                pid              = p.get("Project ID", "")
                already_uploaded = _pc.student_has_uploaded(pid, me)
                badge_lbl        = "Submitted" if already_uploaded else "Pending"
                s_color          = "#34d399" if already_uploaded else "#fbbf24"
                desc_txt         = p.get("Description", "") or ""
                due_txt          = p.get("Due Date", "") or ""
                created          = (p.get("Created At", "") or "")[:10]
                title            = p.get("Title", "Untitled")
                by_              = p.get("Created By", "Teacher")

                exp_label = f"{title}  ·  {badge_lbl}"
                with st.expander(exp_label, expanded=False):
                    # Meta
                    meta_parts = [f"by {by_}", f"created {created}"]
                    if due_txt:
                        meta_parts.append(f"due {due_txt}")
                    st.markdown(
                        f"<div style='display:flex;align-items:center;gap:8px;margin-bottom:10px;'>"
                        f"<span style='width:7px;height:7px;border-radius:50%;"
                        f"background:{s_color};display:inline-block;flex-shrink:0;'></span>"
                        f"<span style='font-size:11px;color:{s_color};font-weight:700;"
                        f"letter-spacing:.05em;'>{badge_lbl.upper()}</span>"
                        f"<span style='font-size:11px;color:#475569;'>"
                        f"{'  ·  '.join(meta_parts)}</span></div>",
                        unsafe_allow_html=True,
                    )
                    if desc_txt:
                        st.markdown(
                            f"<p style='color:#94a3b8;font-size:13px;margin:0 0 12px;"
                            f"line-height:1.6;'>{desc_txt}</p>",
                            unsafe_allow_html=True,
                        )

                    # Teacher reference materials
                    teacher_files = _pc.get_project_files(project_id=pid, uploader_role="teacher")
                    if teacher_files:
                        st.markdown(
                            "<div style='font-size:10px;font-weight:700;color:#38bdf8;"
                            "letter-spacing:.08em;text-transform:uppercase;margin-bottom:6px;'>"
                            "Teacher Materials</div>",
                            unsafe_allow_html=True,
                        )
                        _render_file_folders(teacher_files, f"tf_{pid}")

                    # My submissions
                    my_cl_files = _pc.get_project_files(project_id=pid, uploader=me, uploader_role="student")
                    if my_cl_files:
                        st.markdown(
                            f"<div style='font-size:10px;font-weight:700;color:#a78bfa;"
                            f"letter-spacing:.08em;text-transform:uppercase;margin:12px 0 6px;'>"
                            f"Your submissions  ({len(my_cl_files)})</div>",
                            unsafe_allow_html=True,
                        )
                        _render_file_folders(my_cl_files, f"clf_{pid}")

                    # Submit upload
                    st.markdown(
                        "<div style='margin-top:14px;padding-top:12px;"
                        "border-top:1px solid rgba(255,255,255,.05);'>"
                        "<div style='font-size:10px;font-weight:700;color:#64748b;"
                        "letter-spacing:.08em;text-transform:uppercase;margin-bottom:8px;'>"
                        "Submit Work</div></div>",
                        unsafe_allow_html=True,
                    )
                    _upload_panel(pid, me, "student", f"cl_{pid}")


def teacher_project_page():
    """Teacher view: create class projects, review submissions, view student personal projects."""
    username  = st.session_state.get("username", "")
    full_name = st.session_state.get("student", username)

    page_intro(
        "teacher",
        "Manage projects & student work",
        "Project Center",
        "Create class projects, upload reference materials, and review all student deliverables.",
    )

    tab_create, tab_submissions, tab_student_proj = st.tabs([
        "➕ Create / Manage",
        "📥 Class Submissions",
        "🎓 Student Projects",
    ])

    # ════════════════════════════════════════════════════════════════
    # TAB 1 -- Create & manage class projects
    # ════════════════════════════════════════════════════════════════
    with tab_create:
        st.markdown(
            "<div style='font-size:11px;font-weight:800;color:#38bdf8;letter-spacing:.09em;"
            "text-transform:uppercase;margin-bottom:12px;'>New Class Project</div>",
            unsafe_allow_html=True,
        )

        with st.form("new_class_project_form", border=False):
            c1, c2 = st.columns([2, 1])
            with c1:
                p_title = st.text_input("Project title *", placeholder="e.g. Preluma AI Learning Platform")
                p_desc  = st.text_area("Description *", height=100,
                    placeholder="What should students submit? What is this project about?")
            with c2:
                p_due    = st.text_input("Due date", placeholder="e.g. June 30, 2025")
                p_attach = st.file_uploader(
                    "Attach brief / reference (optional)",
                    type=[e.lstrip(".") for e in _ALLOWED_EXTS],
                    key="proj_teacher_attach",
                )
            create_btn = st.form_submit_button("Create Project", use_container_width=True, type="primary")

        if create_btn:
            if not p_title.strip() or not p_desc.strip():
                st.warning("Title and description are required.")
            else:
                pid = _pc.create_class_project(p_title, p_desc, p_due, full_name or username)
                if p_attach is not None:
                    with st.spinner("Uploading brief..."):
                        _pc.upload_file(
                            project_id    = pid,
                            uploader      = username,
                            uploader_role = "teacher",
                            file_name     = p_attach.name,
                            file_bytes    = p_attach.getvalue(),
                            file_type     = p_attach.type or "",
                            notes         = "Teacher brief",
                        )
                st.success(f"✓ Project created!")
                st.rerun()

        # List existing class projects
        class_projects = _pc.load_class_projects()
        if class_projects:
            st.markdown(
                "<div style='font-size:11px;font-weight:800;color:#818cf8;letter-spacing:.09em;"
                "text-transform:uppercase;margin:20px 0 10px;'>Existing Projects</div>",
                unsafe_allow_html=True,
            )
            for p in class_projects:
                pid = p.get("Project ID", "")
                _project_card(p)

                teacher_files = _pc.get_project_files(project_id=pid, uploader_role="teacher")
                if teacher_files:
                    st.markdown(
                        "<div style='font-size:11px;color:#64748b;margin:6px 0 3px;'>Uploaded materials:</div>",
                        unsafe_allow_html=True,
                    )
                    for i, tf in enumerate(teacher_files):
                        st.markdown(
                            f"<div style='font-size:12px;color:#94a3b8;padding:3px 0;'>"
                            f"{_file_icon(tf.get('file_name',''))} {tf.get('file_name','')}"
                            f" · <span style='color:#475569;'>{tf.get('created_at','')[:10]}</span></div>",
                            unsafe_allow_html=True,
                        )

                with st.expander(f"Upload more material for: {p.get('Title','')}"):
                    more_up = st.file_uploader(
                        "Additional file",
                        type=[e.lstrip(".") for e in _ALLOWED_EXTS],
                        key=f"more_up_{pid}",
                    )
                    more_notes = st.text_input("Label", key=f"more_notes_{pid}",
                                               placeholder="e.g. Slides v2")
                    if more_up and st.button("Upload", key=f"more_btn_{pid}", type="primary"):
                        with st.spinner("Uploading..."):
                            ok, fid = _pc.upload_file(
                                project_id    = pid,
                                uploader      = username,
                                uploader_role = "teacher",
                                file_name     = more_up.name,
                                file_bytes    = more_up.getvalue(),
                                file_type     = more_up.type or "",
                                notes         = more_notes,
                            )
                        if ok:
                            st.success("✓ Uploaded!")
                            st.rerun()
                        else:
                            st.error("Upload failed.")
                st.markdown("<div style='height:8px;'></div>", unsafe_allow_html=True)

    # ════════════════════════════════════════════════════════════════
    # TAB 2 -- Class project submissions from students
    # ════════════════════════════════════════════════════════════════
    with tab_submissions:
        class_projects = _pc.load_class_projects()
        if not class_projects:
            st.info("No class projects yet. Create one in the first tab.")
        else:
            sel_titles = {p.get("Title", ""): p.get("Project ID", "") for p in class_projects}
            sel = st.selectbox("Select project", list(sel_titles.keys()), key="teacher_proj_sel")
            sel_pid = sel_titles.get(sel, "")

            if sel_pid:
                student_files = _pc.get_project_files(project_id=sel_pid, uploader_role="student")

                if not student_files:
                    st.markdown(
                        "<div style='padding:18px;text-align:center;color:#64748b;'>"
                        "No submissions yet for this project.</div>",
                        unsafe_allow_html=True,
                    )
                else:
                    by_student: dict[str, list] = {}
                    for sf in student_files:
                        s = sf.get("uploader", "Unknown")
                        by_student.setdefault(s, []).append(sf)

                    st.markdown(
                        f"<div style='font-size:12px;color:#94a3b8;margin-bottom:12px;'>"
                        f"<b style='color:#e2e8f0;'>{len(student_files)}</b> file(s) from "
                        f"<b style='color:#e2e8f0;'>{len(by_student)}</b> student(s)</div>",
                        unsafe_allow_html=True,
                    )

                    for sname, files in sorted(by_student.items()):
                        cnt = len(files)
                        plur = "s" if cnt > 1 else ""
                        with st.expander(f"👤 {sname}  ({cnt} file{plur})", expanded=True):
                            for i, sf in enumerate(sorted(files, key=lambda x: x.get("created_at",""), reverse=True)):
                                _file_row(sf, f"dl_st_{sel_pid}_{sname}_{i}", f"sv_st_{sel_pid}_{sname}_{i}")

    # ════════════════════════════════════════════════════════════════
    # TAB 3 -- Completed personal projects from all students
    # ════════════════════════════════════════════════════════════════
    with tab_student_proj:
        personal_complete = _pc.load_all_complete_personal_projects()

        if not personal_complete:
            st.markdown(
                "<div style='background:rgba(52,211,153,.05);border:1px solid rgba(52,211,153,.12);"
                "border-radius:16px;padding:22px;text-align:center;color:#94a3b8;'>"
                "No completed student projects yet. Students mark their personal projects as "
                "<b>Complete</b> to share them here.</div>",
                unsafe_allow_html=True,
            )
        else:
            # Group by student owner
            by_owner: dict[str, list] = {}
            for pp in personal_complete:
                owner = pp.get("Owner") or pp.get("Created By", "Unknown")
                by_owner.setdefault(owner, []).append(pp)

            st.markdown(
                f"<div style='font-size:12px;color:#94a3b8;margin-bottom:14px;'>"
                f"<b style='color:#e2e8f0;'>{len(personal_complete)}</b> completed project(s) "
                f"from <b style='color:#e2e8f0;'>{len(by_owner)}</b> student(s)</div>",
                unsafe_allow_html=True,
            )

            for owner_name, projects_list in sorted(by_owner.items()):
                cnt = len(projects_list)
                plur = "s" if cnt > 1 else ""
                with st.expander(f"🎓 {owner_name}  ({cnt} project{plur})", expanded=True):
                    for proj in sorted(projects_list, key=lambda x: x.get("Created At",""), reverse=True):
                        ppid = proj.get("Project ID", "")
                        _project_card(proj, "Complete", "#34d399")

                        # Files uploaded to this personal project
                        proj_files = _pc.get_project_files(project_id=ppid)
                        if proj_files:
                            st.markdown(
                                f"<div style='font-size:11px;color:#64748b;margin:6px 0 4px;'>"
                                f"{len(proj_files)} file(s)</div>",
                                unsafe_allow_html=True,
                            )
                            for i, pf in enumerate(sorted(proj_files, key=lambda x: x.get("created_at",""), reverse=True)):
                                _file_row(pf, f"dl_pp_{ppid}_{i}", f"sv_pp_{ppid}_{i}")
                        else:
                            st.markdown(
                                "<div style='font-size:12px;color:#475569;padding:6px 0;'>"
                                "No files uploaded for this project.</div>",
                                unsafe_allow_html=True,
                            )
                        st.markdown("<div style='height:10px;'></div>", unsafe_allow_html=True)

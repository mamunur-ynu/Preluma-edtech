"""Student profile, teacher profile and teacher detail pages."""

from __future__ import annotations

from pathlib import Path

import streamlit as st

from auth import esc
from services.user_service import student_number

from components.ui_components import get_photo_src as _get_photo_src
from components.ui_components import page_intro
from config import get_setting as _get_secret
from services.homework_service import create_homework
from services.homework_service import hw_num
from services.media_service import delete_photo as _delete_photo_sb
from services.media_service import save_photo as _save_photo_sb
from services.upload_service import HOMEWORK_POLICY, PROFILE_IMAGE_POLICY, store_private_upload
from security.uploads import validate_upload
from views.homework import default_homework_questions

def student_profile_page():
    """Premium student profile -- hero banner, rank, stats, activity."""
    username  = st.session_state.get("username", "")
    full_name = st.session_state.get("student", username)

    # ── Compute stats ─────────────────────────────────────────────────────────
    from services.homework_service import load_submissions, load_student_mistakes, homework_for_student
    all_subs    = load_submissions()
    my_subs     = [s for s in all_subs
                   if str(s.get("Student","")).strip().casefold() == full_name.strip().casefold()]
    my_mistakes = load_student_mistakes(full_name)
    my_hw       = homework_for_student(full_name)
    _hw_by_id   = {h.get("Homework ID", ""): h for h in my_hw}  # lookup for hw_number/title
    _snum       = student_number(username)  # sequential student number

    total_submitted = len(my_subs)
    percentages: list[float] = []
    for s in my_subs:
        try: percentages.append(float(s.get("Percentage", 0)))
        except (TypeError, ValueError): pass
    avg_score   = round(sum(percentages) / len(percentages), 1) if percentages else 0.0
    best_score  = max(percentages) if percentages else 0.0
    mistake_cnt = len(my_mistakes)
    hw_assigned = len(my_hw)
    completion  = round((total_submitted / hw_assigned) * 100) if hw_assigned else 0

    def _sc(pct: float) -> str:
        if pct >= 80: return "#34d399"
        if pct >= 60: return "#fbbf24"
        return "#f87171"

    # ── Rank system ──────────────────────────────────────────────────────────
    RANKS = [
        (91, "🏆", "Master",   "#fbbf24"),
        (76, "🎓", "Scholar",  "#a78bfa"),
        (61, "⭐", "Achiever", "#38bdf8"),
        (41, "🔍", "Explorer", "#34d399"),
        ( 0, "🌱", "Beginner", "#94a3b8"),
    ]
    rank_emoji, rank_name, rank_color = "🌱", "Beginner", "#94a3b8"
    for min_pct, re, rn, rc in RANKS:
        if avg_score >= min_pct:
            rank_emoji, rank_name, rank_color = re, rn, rc
            break
    # Progress to next rank
    next_threshold = 100
    for min_pct, _, _, _ in RANKS:
        if min_pct > avg_score:
            next_threshold = min_pct
    rank_progress = min(100, round((avg_score / next_threshold) * 100)) if next_threshold else 100

    # ── Avatar ────────────────────────────────────────────────────────────────
    photo_src = _get_photo_src(username)
    initials  = "".join(w[0].upper() for w in full_name.split()[:2]) if full_name else "?"
    if photo_src:
        avatar_inner = f"<img src='{photo_src}' style='width:100%;height:100%;object-fit:cover;border-radius:50%;display:block;'>"
    else:
        avatar_inner = f"<span style='font-size:34px;font-weight:900;color:#38bdf8;'>{initials}</span>"

    # ── Hero HTML ─────────────────────────────────────────────────────────────
    bar_c  = _sc(completion)
    avg_c  = _sc(avg_score)
    best_c = _sc(best_score)

    _snum_badge = f"<span style='display:inline-flex;align-items:center;gap:5px;background:rgba(56,189,248,.12);border:1px solid rgba(56,189,248,.30);color:#38bdf8;font-size:11px;font-weight:800;padding:3px 10px;border-radius:20px;letter-spacing:.04em;'>#{_snum}</span>" if _snum else ""

    st.markdown(f"""<style>
.sp-hero {{
    border-radius:28px; overflow:hidden;
    border:1px solid rgba(56,189,248,.12);
    background:linear-gradient(170deg,#060e1c 0%,#0b1930 60%,#060e1c 100%);
    margin-bottom:24px;
    box-shadow: 0 20px 60px rgba(0,0,0,.5);
}}
.sp-banner {{
    height:130px; position:relative; overflow:hidden;
    background:linear-gradient(135deg,#0a1f3d 0%,#12103a 40%,#0d2040 70%,#071530 100%);
}}
.sp-banner::before {{
    content:''; position:absolute; inset:0;
    background:
        radial-gradient(ellipse at 10% 50%, rgba(56,189,248,.28) 0%, transparent 45%),
        radial-gradient(ellipse at 90% 30%, rgba(139,92,246,.22) 0%, transparent 45%),
        radial-gradient(ellipse at 55% 90%, rgba(52,211,153,.12) 0%, transparent 45%),
        radial-gradient(ellipse at 70% 10%, rgba(56,189,248,.10) 0%, transparent 35%);
}}
.sp-banner::after {{
    content:''; position:absolute; inset:0;
    background: repeating-linear-gradient(
        0deg, transparent, transparent 28px,
        rgba(255,255,255,.018) 28px, rgba(255,255,255,.018) 29px
    ),
    repeating-linear-gradient(
        90deg, transparent, transparent 28px,
        rgba(255,255,255,.018) 28px, rgba(255,255,255,.018) 29px
    );
}}
.sp-body {{ padding:0 28px 28px; }}
.sp-top {{ display:flex; align-items:flex-end; gap:20px; margin-bottom:20px; }}
.sp-avatar-outer {{
    position:relative; flex-shrink:0; margin-top:-54px;
}}
.sp-avatar-glow {{
    width:108px; height:108px; border-radius:50%;
    background:radial-gradient(circle, {rank_color}22 0%, transparent 70%);
    position:absolute; inset:-8px;
    box-shadow: 0 0 30px {rank_color}33;
}}
.sp-avatar-ring {{
    width:104px; height:104px; border-radius:50%;
    background:linear-gradient(145deg,#1a3050,#0d1f35);
    border:3px solid #060e1c;
    box-shadow: 0 0 0 2.5px {rank_color}70, 0 12px 36px rgba(0,0,0,.65);
    display:flex; align-items:center; justify-content:center;
    overflow:hidden; position:relative; z-index:1;
}}
.sp-info {{ padding-bottom:4px; min-width:0; flex:1; }}
.sp-name {{ font-size:24px; font-weight:900; color:#f1f5f9; line-height:1.2; letter-spacing:-.3px; }}
.sp-meta {{ display:flex; align-items:center; gap:8px; margin-top:5px; flex-wrap:wrap; }}
.sp-un   {{ font-size:12px; color:#475569; font-weight:600; }}
.sp-tags {{ display:flex; gap:7px; margin-top:10px; flex-wrap:wrap; }}
.sp-tag  {{
    font-size:10px; font-weight:800; letter-spacing:.08em; text-transform:uppercase;
    padding:4px 12px; border-radius:20px;
}}
.sp-stats {{
    display:grid; grid-template-columns:repeat(4,1fr); gap:10px; margin-bottom:20px;
}}
.sp-stat {{
    border-radius:18px; padding:16px 8px 14px; text-align:center;
    background:rgba(6,14,28,.75); border:1px solid rgba(255,255,255,.07);
    position:relative; overflow:hidden;
}}
.sp-stat-accent {{
    position:absolute; top:0; left:0; right:0; height:3px; border-radius:18px 18px 0 0;
}}
.sp-sv {{ font-size:26px; font-weight:900; line-height:1.15; margin-top:4px; }}
.sp-si {{ font-size:16px; margin-bottom:0; }}
.sp-sl {{ font-size:9px; color:#475569; font-weight:700; letter-spacing:.10em;
          text-transform:uppercase; margin-top:4px; }}
.sp-progress-block {{ margin-bottom:12px; }}
.sp-prog-label {{
    display:flex; justify-content:space-between; align-items:center;
    margin-bottom:6px;
}}
.sp-prog-lbl {{ font-size:11px; color:#64748b; font-weight:700; }}
.sp-prog-val {{ font-size:11px; font-weight:800; }}
.sp-bar-wrap {{
    background:rgba(255,255,255,.05); border-radius:8px; height:9px; overflow:hidden;
}}
.sp-bar-fill {{ height:100%; border-radius:8px; }}
.sp-section-lbl {{
    font-size:10px; font-weight:800; color:#475569; letter-spacing:.12em;
    text-transform:uppercase; margin:22px 0 10px;
    display:flex; align-items:center; gap:8px;
}}
.sp-section-lbl::after {{
    content:''; flex:1; height:1px; background:rgba(255,255,255,.06);
}}
.sp-sub-row {{
    display:flex; align-items:center; gap:14px;
    background:rgba(6,14,28,.65); border:1px solid rgba(255,255,255,.06);
    border-radius:16px; padding:13px 16px; margin-bottom:8px;
    transition: border-color .2s;
}}
.sp-sub-score {{
    width:50px; height:50px; border-radius:14px;
    display:flex; align-items:center; justify-content:center;
    font-size:13px; font-weight:900; flex-shrink:0;
}}
</style>
""", unsafe_allow_html=True)

    st.markdown(
f"<div class='sp-hero'>"
f"<div class='sp-banner'></div>"
f"<div class='sp-body'>"
f"<div class='sp-top'>"
f"<div class='sp-avatar-outer'>"
f"<div class='sp-avatar-glow'></div>"
f"<div class='sp-avatar-ring'>{avatar_inner}</div>"
f"</div>"
f"<div class='sp-info'>"
f"<div class='sp-name'>{esc(full_name)}</div>"
f"<div class='sp-meta'>"
f"<span class='sp-un'>@{esc(username)}</span>"
+ (_snum_badge)
+ f"</div>"
f"<div class='sp-tags'>"
f"<span class='sp-tag' style='background:rgba(52,211,153,.10);border:1px solid rgba(52,211,153,.25);color:#34d399;'>✦ STUDENT</span>"
f"<span class='sp-tag' style='background:{rank_color}15;border:1px solid {rank_color}45;color:{rank_color};'>{rank_emoji} {rank_name}</span>"
f"</div></div></div>"
f"<div class='sp-stats'>"
f"<div class='sp-stat'><div class='sp-stat-accent' style='background:linear-gradient(90deg,#38bdf8,#0ea5e9);'></div>"
f"<div class='sp-si'>📝</div><div class='sp-sv' style='color:#38bdf8;'>{total_submitted}</div><div class='sp-sl'>Submitted</div></div>"
f"<div class='sp-stat'><div class='sp-stat-accent' style='background:linear-gradient(90deg,{avg_c},{avg_c}88);'></div>"
f"<div class='sp-si'>📊</div><div class='sp-sv' style='color:{avg_c};'>{avg_score:.0f}%</div><div class='sp-sl'>Avg Score</div></div>"
f"<div class='sp-stat'><div class='sp-stat-accent' style='background:linear-gradient(90deg,{best_c},{best_c}88);'></div>"
f"<div class='sp-si'>🏅</div><div class='sp-sv' style='color:{best_c};'>{best_score:.0f}%</div><div class='sp-sl'>Best Score</div></div>"
f"<div class='sp-stat'><div class='sp-stat-accent' style='background:linear-gradient(90deg,#f87171,#ef444488);'></div>"
f"<div class='sp-si'>⚠️</div><div class='sp-sv' style='color:#f87171;'>{mistake_cnt}</div><div class='sp-sl'>Weak Areas</div></div>"
f"</div>"
f"<div class='sp-progress-block'>"
f"<div class='sp-prog-label'>"
f"<span class='sp-prog-lbl'>📚 Homework Completion</span>"
f"<span class='sp-prog-val' style='color:{bar_c};'>{completion}% &nbsp;({total_submitted}/{hw_assigned})</span>"
f"</div>"
f"<div class='sp-bar-wrap'><div class='sp-bar-fill' style='width:{completion}%;background:linear-gradient(90deg,{bar_c}88,{bar_c});'></div></div>"
f"</div>"
f"<div class='sp-progress-block'>"
f"<div class='sp-prog-label'>"
f"<span class='sp-prog-lbl'>{rank_emoji} Progress to {rank_name}</span>"
f"<span class='sp-prog-val' style='color:{rank_color};'>{rank_progress}%</span>"
f"</div>"
f"<div class='sp-bar-wrap'><div class='sp-bar-fill' style='width:{rank_progress}%;background:linear-gradient(90deg,{rank_color}77,{rank_color});box-shadow:0 0 8px {rank_color}44;'></div></div>"
f"</div>"
f"</div></div>",
unsafe_allow_html=True)

    # ── Recent Submissions ─────────────────────────────────────────────────────
    if my_subs:
        st.markdown("<div class='sp-section-lbl'>Recent Submissions</div>", unsafe_allow_html=True)
        for sub in sorted(my_subs, key=lambda s: s.get("Submitted At",""), reverse=True)[:5]:
            pct = float(sub.get("Percentage", 0) or 0)
            sc  = _sc(pct)
            _hw_row  = _hw_by_id.get(sub.get("Homework ID", ""), {})
            _hw_n    = hw_num(_hw_row) if _hw_row else hw_num(sub)
            _hw_ttl  = _hw_row.get("Title", "") or ""
            st.markdown(
                f"<div class='sp-sub-row'>"
                f"<div class='sp-sub-score' style='background:{sc}14;color:{sc};'>{pct:.0f}%</div>"
                f"<div style='flex:1;min-width:0;'>"
                f"<div style='font-size:14px;font-weight:700;color:#e2e8f0;"
                f"white-space:nowrap;overflow:hidden;text-overflow:ellipsis;'>"
                f"HW #{_hw_n}"
                + (f" <span style='font-size:13px;color:#94a3b8;font-weight:500;'>· {_hw_ttl}</span>" if _hw_ttl else "")
                + f" &nbsp;<span style='font-size:11px;font-weight:500;color:#475569;'>· {sub.get('Score','')}/{sub.get('Total','')} pts</span>"
                f"</div>"
                f"<div style='font-size:11px;color:#334155;margin-top:3px;'>"
                f"Attempt #{sub.get('Attempt','1')} &nbsp;·&nbsp; {sub.get('Submitted At','')[:16]}"
                f"</div></div>"
                f"<div style='font-size:11px;font-weight:800;color:{sc};flex-shrink:0;'>"
                f"{'✓' if pct >= 60 else '✗'}</div>"
                f"</div>",
                unsafe_allow_html=True,
            )
    else:
        st.markdown(
            "<div style='text-align:center;padding:28px;color:#334155;font-size:13px;'>"
            "No homework submissions yet.</div>",
            unsafe_allow_html=True,
        )

    # ── Weak Areas -- grouped by HW, with question details ────────────────────
    if my_mistakes:
        # Group mistakes by homework ID
        _mistakes_by_hw: dict[str, list] = {}
        for m in my_mistakes:
            hid = m.get("Homework ID", "")
            _mistakes_by_hw.setdefault(hid, []).append(m)

        with st.expander(f"⚠️ Weak Areas  ({mistake_cnt}  wrong answers)", expanded=False):
            for hid, hw_mistakes in _mistakes_by_hw.items():
                _hw_meta = _hw_by_id.get(hid, {})
                _hw_label = f"HW #{hw_num(_hw_meta) if _hw_meta else hid[:6]}"
                _hw_title = _hw_meta.get("Title", "")
                # HW header
                st.markdown(
                    f"<div style='display:flex;align-items:center;gap:10px;"
                    f"margin:14px 0 8px;'>"
                    f"<span style='background:rgba(248,113,113,.12);border:1px solid rgba(248,113,113,.25);"
                    f"color:#fca5a5;font-size:11px;font-weight:800;padding:3px 10px;border-radius:12px;'>"
                    f"{_hw_label}</span>"
                    + (f"<span style='font-size:13px;font-weight:700;color:#cbd5e1;'>{_hw_title}</span>" if _hw_title else "")
                    + f"<span style='font-size:11px;color:#475569;'>· {len(hw_mistakes)} mistake{'s' if len(hw_mistakes)>1 else ''}</span>"
                    f"</div>",
                    unsafe_allow_html=True,
                )
                # Each wrong question
                for idx, m in enumerate(hw_mistakes):
                    concept   = m.get("Weak Concept", "") or "General"
                    question  = m.get("Question", "")
                    s_ans     = m.get("Student Answer", "")
                    c_ans     = m.get("Correct Answer", "")
                    expl      = m.get("Explanation", "")
                    _q_html  = (
                        f"<div style='background:rgba(6,14,28,.75);border:1px solid rgba(248,113,113,.15);"
                        f"border-left:3px solid #f87171;border-radius:12px;padding:14px 16px;margin-bottom:10px;'>"
                        f"<div style='margin-bottom:8px;'>"
                        f"<span style='background:rgba(248,113,113,.10);border:1px solid rgba(248,113,113,.22);"
                        f"color:#fca5a5;font-size:10px;font-weight:800;padding:2px 9px;border-radius:10px;"
                        f"letter-spacing:.05em;text-transform:uppercase;'>📌 {concept}</span>"
                        f"</div>"
                    )
                    if question:
                        _q_html += (
                            f"<div style='font-size:13px;color:#e2e8f0;font-weight:600;"
                            f"margin-bottom:10px;line-height:1.5;'>{question}</div>"
                        )
                    _q_html += "<div style='display:flex;gap:10px;flex-wrap:wrap;'>"
                    if s_ans:
                        _q_html += (
                            f"<div style='flex:1;min-width:140px;background:rgba(248,113,113,.08);"
                            f"border:1px solid rgba(248,113,113,.20);border-radius:8px;padding:8px 12px;'>"
                            f"<div style='font-size:9px;color:#f87171;font-weight:800;"
                            f"letter-spacing:.08em;margin-bottom:3px;'>✗ YOUR ANSWER</div>"
                            f"<div style='font-size:13px;color:#fca5a5;font-weight:700;'>{s_ans}</div>"
                            f"</div>"
                        )
                    if c_ans:
                        _q_html += (
                            f"<div style='flex:1;min-width:140px;background:rgba(52,211,153,.08);"
                            f"border:1px solid rgba(52,211,153,.20);border-radius:8px;padding:8px 12px;'>"
                            f"<div style='font-size:9px;color:#34d399;font-weight:800;"
                            f"letter-spacing:.08em;margin-bottom:3px;'>✓ CORRECT ANSWER</div>"
                            f"<div style='font-size:13px;color:#6ee7b7;font-weight:700;'>{c_ans}</div>"
                            f"</div>"
                        )
                    _q_html += "</div>"
                    if expl:
                        _q_html += (
                            f"<div style='margin-top:10px;font-size:12px;color:#64748b;"
                            f"line-height:1.55;border-top:1px solid rgba(255,255,255,.05);padding-top:8px;'>"
                            f"💡 {expl}</div>"
                        )
                    _q_html += "</div>"
                    st.markdown(_q_html, unsafe_allow_html=True)

    # ── Profile Photo Upload ──────────────────────────────────────────────────
    st.markdown("<div style='height:10px;'></div>", unsafe_allow_html=True)
    with st.expander("📷 Update Profile Photo", expanded=False):
        st.markdown(
            "<div style='font-size:12px;color:#64748b;margin-bottom:10px;'>"
            "Upload a photo (JPG or PNG, max 5 MB). It will appear on your profile card.</div>",
            unsafe_allow_html=True,
        )
        photo_up = st.file_uploader(
            "Choose photo — max 5 MB (JPG or PNG only)",
            type=["jpg", "jpeg", "png"],
            key="profile_photo_up",
            help="Profile photos must be under 5 MB. Larger files will be rejected.",
        )
        c1, c2 = st.columns(2)
        if photo_up is not None:
            size_mb = photo_up.size / (1024 * 1024)
            if size_mb > 5:
                st.warning(f"Photo too large ({size_mb:.1f} MB). Max is 5 MB.")
            elif c1.button("💾 Save Photo", key="save_photo_btn", type="primary",
                           use_container_width=True):
                try:
                    checked = validate_upload(photo_up.name, photo_up.getvalue(), PROFILE_IMAGE_POLICY)
                    ext = "jpeg" if checked.extension in {".jpg", ".jpeg"} else checked.extension.lstrip(".")
                    with st.spinner("Saving photo..."):
                        photos_dir = Path("photos")
                        photos_dir.mkdir(exist_ok=True)
                        (photos_dir / f"{username}.{ext}").write_bytes(checked.data)
                        st.session_state.pop(f"_sbp_{username}", None)
                        saved_ok, _err = _save_photo_sb(username, checked.data, ext)
                    if saved_ok:
                        st.success("✓ Photo saved permanently!")
                    else:
                        st.error(f"❌ Supabase save failed: `{_err}`")
                    st.rerun()
                except ValueError as exc:
                    st.error(str(exc))

        if photo_src:
            if c2.button("🗑 Remove Photo", key="del_photo_btn", use_container_width=True):
                with st.spinner("Removing..."):
                    photos_dir = Path("photos")
                    for ext in ("jpg", "jpeg", "png", "webp"):
                        fp = photos_dir / f"{username}.{ext}"
                        if fp.exists():
                            fp.unlink()
                    st.session_state.pop(f"_sbp_{username}", None)
                    _delete_photo_sb(username)
                st.success("✓ Photo removed.")
                st.rerun()
        elif photo_up is None:
            st.info("Select a photo above, then click Save Photo.")

    # ── Profile Info (university, ID, major, etc.) ───────────────────────────
    st.markdown("<div style='height:10px;'></div>", unsafe_allow_html=True)

    # Load saved profile extras from Supabase
    def _load_profile_extras(uname: str) -> dict:
        try:
            import requests as _req
            sb_url = _get_secret("SUPABASE_URL").rstrip("/")
            sb_key = _get_secret("SUPABASE_KEY")
            if not sb_url or not sb_key:
                return {}
            resp = _req.get(
                f"{sb_url}/rest/v1/preluma_profiles",
                headers={"apikey": sb_key, "Authorization": f"Bearer {sb_key}"},
                params={"username": f"eq.{uname}", "select": "*"},
                timeout=5,
            )
            rows = resp.json()
            return rows[0] if rows else {}
        except Exception:
            return {}

    def _save_profile_extras(uname: str, data: dict) -> None:
        try:
            import requests as _req
            sb_url = _get_secret("SUPABASE_URL").rstrip("/")
            sb_key = _get_secret("SUPABASE_KEY")
            if not sb_url or not sb_key:
                return
            payload = {"username": uname, **data}
            _req.post(
                f"{sb_url}/rest/v1/preluma_profiles",
                headers={
                    "apikey": sb_key,
                    "Authorization": f"Bearer {sb_key}",
                    "Content-Type": "application/json",
                    "Prefer": "resolution=merge-duplicates,return=minimal",
                },
                json=payload,
                timeout=5,
            )
        except Exception:  # nosec B110
            pass

    cache_key = f"_profile_extras_{username}"
    if cache_key not in st.session_state:
        st.session_state[cache_key] = _load_profile_extras(username)
    extras = st.session_state[cache_key]

    with st.expander("✏️ Edit Profile Info", expanded=not bool(extras.get("university"))):
        with st.form("profile_info_form"):
            col1, col2 = st.columns(2)
            with col1:
                p_university = st.text_input("University", value=extras.get("university", "Yunnan University"))
                p_student_id = st.text_input("Student ID", value=extras.get("student_id", ""))
                p_major      = st.text_input("Major", value=extras.get("major", ""))
            with col2:
                p_age        = st.text_input("Age", value=extras.get("age", ""))
                p_hobby      = st.text_input("Hobbies", value=extras.get("hobby", ""))
                p_interest   = st.text_input("Interests", value=extras.get("interest", ""))
            if st.form_submit_button("💾 Save Profile Info", type="primary", use_container_width=True):
                new_extras = {
                    "university": p_university,
                    "student_id": p_student_id,
                    "major":      p_major,
                    "age":        p_age,
                    "hobby":      p_hobby,
                    "interest":   p_interest,
                }
                _save_profile_extras(username, new_extras)
                st.session_state[cache_key] = new_extras
                st.success("✓ Profile info saved!")
                st.rerun()

    # Show info cards if filled
    if any(extras.get(k) for k in ("university", "student_id", "major", "age", "hobby", "interest")):
        info_html = "<div style='display:flex;flex-wrap:wrap;gap:10px;margin-top:8px;'>"
        icons = {"university": "🏫", "student_id": "🪪", "major": "📚", "age": "🎂", "hobby": "🎯", "interest": "💡"}
        labels = {"university": "University", "student_id": "Student ID", "major": "Major", "age": "Age", "hobby": "Hobbies", "interest": "Interests"}
        for k, icon in icons.items():
            val = extras.get(k, "")
            if val:
                info_html += (
                    f"<div style='background:rgba(30,41,59,.7);border:1px solid rgba(100,116,139,.25);"
                    f"border-radius:12px;padding:10px 16px;min-width:140px;'>"
                    f"<div style='font-size:11px;color:#64748b;font-weight:700;'>{icon} {labels[k].upper()}</div>"
                    f"<div style='font-size:14px;color:#e2e8f0;font-weight:600;margin-top:3px;'>{val}</div>"
                    f"</div>"
                )
        info_html += "</div>"
        st.markdown(info_html, unsafe_allow_html=True)


def teacher_profile_page():
    """Compact name-card grid -- click to open full detail page."""
    page_intro(
        "teacher",
        "Course Teachers · Yunnan University",
        "Teacher Profile",
        "The teaching team behind this course. Click a card to view the full profile.",
    )

    TEACHERS = teacher_list()

    st.markdown("""
    <style>
    .tpg-grid { display:grid; grid-template-columns:1fr 1fr; gap:16px; margin-bottom:8px; }
    .tpg-card {
        background:linear-gradient(145deg,rgba(10,18,36,.97),rgba(6,12,26,.99));
        border:1px solid rgba(255,255,255,.07); border-radius:20px;
        padding:20px; display:flex; align-items:center; gap:16px;
    }
    .tpg-av {
        width:60px; height:60px; border-radius:50%; flex-shrink:0;
        background:linear-gradient(135deg,#0ea5e9,#6366f1);
        display:flex; align-items:center; justify-content:center;
        font-size:20px; font-weight:900; color:#fff;
        border:2px solid rgba(56,189,248,.3);
        object-fit:cover;
    }
    .tpg-name { font-size:17px; font-weight:800; color:#f1f5f9; margin-bottom:2px; }
    .tpg-cn   { font-size:13px; color:#38bdf8; margin-bottom:3px; }
    .tpg-role { font-size:11px; color:#64748b; }
    </style>
    """, unsafe_allow_html=True)

    col1, col2 = st.columns(2)
    cols = [col1, col2, col1, col2]
    for idx, t in enumerate(TEACHERS):
        photo_src = _get_photo_src(t["photo_key"])
        av = f'<img src="{photo_src}" class="tpg-av" width="60" height="60" style="width:60px;height:60px;object-fit:cover;border-radius:50%;flex-shrink:0;">' if photo_src else f'<div class="tpg-av">{t["initials"]}</div>'
        with cols[idx]:
            st.markdown(f"""
            <div class="tpg-card">
                {av}
                <div>
                    <div class="tpg-name">{t["name"]}</div>
                    <div class="tpg-cn">{t["cn"]}</div>
                    <div class="tpg-role">{t["role"]}</div>
                </div>
            </div>""", unsafe_allow_html=True)
            if st.button("View Full Profile →", key=f"tpg_open_{idx}", use_container_width=True):
                st.session_state.tp_detail_idx = idx
                st.session_state.active_page = "teacher_detail"
                st.rerun()

    # ── Quick Assign Homework (full form, same as Homework Center) ──
    st.markdown("""<div style="font-size:10px;font-weight:800;color:#f59e0b;letter-spacing:.10em;
        text-transform:uppercase;margin:32px 0 16px;">Quick Assign Homework</div>""",
        unsafe_allow_html=True)

    _TEACHER_OPTIONS = [
        "Zhou Yujue (周玉珏) · AI Dept",
        "Gao Song (高嵩) · Software Engineering",
        "Tang Li (唐丽) · Cyberspace Security",
        "Wei Ping (韦平) · Cyberspace Security",
    ]
    _TEACHER_NAMES = {
        "Zhou Yujue (周玉珏) · AI Dept":          "Zhou Yujue",
        "Gao Song (高嵩) · Software Engineering": "Gao Song",
        "Tang Li (唐丽) · Cyberspace Security":    "Tang Li",
        "Wei Ping (韦平) · Cyberspace Security":   "Wei Ping",
    }
    _logged_name = st.session_state.get("student", "") or ""
    _default_idx = 0
    for _i, _k in enumerate(_TEACHER_OPTIONS):
        if _logged_name.split()[0] in _k if _logged_name.split() else False:
            _default_idx = _i

    # File uploader must live outside the form
    tp_uploaded = st.file_uploader(
        "Attach homework file (optional)",
        type=["pdf", "doc", "docx", "txt"],
        help="Upload a PDF or Word document as homework reference material.",
        key="tp_hw_file",
    )
    tp_attachment = ""
    if tp_uploaded is not None:
        try:
            stored = store_private_upload(
                "homework_attachments", tp_uploaded.name, tp_uploaded.getvalue(), HOMEWORK_POLICY
            )
            tp_attachment = stored.relative_path
            st.success(f"📎 File ready: {stored.filename}")
        except ValueError as exc:
            st.error(str(exc))

    with st.form("tp_quick_assign", border=False):
        tp_teacher = st.selectbox(
            "Assigned by (Teacher)", _TEACHER_OPTIONS, index=_default_idx,
            help="Select which teacher is publishing this homework.",
        )
        qa1, qa2 = st.columns(2)
        hw_title = qa1.text_input("Homework title", value="Introduction Practice")
        hw_topic = qa2.text_input("Topic", value="Machine Learning")
        hw_instr = st.text_area("Instructions",
            value="Read the topic summary and answer all questions.")
        qa3, qa4, qa5 = st.columns(3)
        hw_due    = qa3.text_input("Due date", value="Friday 8:00 PM")
        hw_diff   = qa4.selectbox("Difficulty", ["Beginner", "Intermediate", "Advanced"])
        hw_assign = qa5.text_input("Assign to", value="All Students",
            help="All Students or comma-separated names.")
        submit_hw = st.form_submit_button("Publish Homework", use_container_width=True)

    if submit_hw:
        if hw_title.strip() and hw_topic.strip():
            hw_id, new_hw_number = create_homework(
                title=hw_title.strip(),
                topic=hw_topic.strip(),
                instructions=hw_instr.strip(),
                due_date=hw_due.strip() or "TBD",
                difficulty=hw_diff,
                assigned_to=hw_assign.strip() or "All Students",
                created_by=tp_teacher,
                questions=default_homework_questions(hw_topic.strip()),
                attachment=tp_attachment,
            )
            tname = _TEACHER_NAMES.get(tp_teacher, tp_teacher)
            st.success(f"✅ Homework #{new_hw_number} published by **{tname}**. Students have been notified.")
        else:
            st.warning("Please fill in the title and topic.")


def teacher_list():
    return [
        {"initials":"ZY","name":"Zhou Yujue","cn":"周玉珏","photo_key":"zhouyujue",
         "role":"Lecturer · AI Department","course":"Python Programming & AI Tools",
         "research":"AI, Time Series Analysis, Smart Healthcare","email":"zhouyujue@ynu.edu.cn"},
        {"initials":"GS","name":"Gao Song","cn":"高嵩","photo_key":"gaosong",
         "role":"Lecturer · Software Engineering","course":"C++ Programming",
         "research":"Computer Vision, AI Security, Model Compression","email":"gaos@ynu.edu.cn"},
        {"initials":"TL","name":"Tang Li","cn":"唐丽","photo_key":"tangli",
         "role":"Lecturer · Cyberspace Security","course":"Database",
         "research":"Data Security, Image Security","email":"tangli@ynu.edu.cn"},
        {"initials":"WP","name":"Wei Ping","cn":"韦平","photo_key":"weiping",
         "role":"Lecturer · Cyberspace Security","course":"Statistics & Probability",
         "research":"LLM & Multi-agent, Cybersecurity, Multimedia Security","email":"weip@ynu.edu.cn"},
    ]


def teacher_detail_page():
    """Full-page beautiful profile for a single teacher."""
    import pathlib as _pl

    TEACHERS = teacher_list()
    idx = st.session_state.get("tp_detail_idx", 0)
    if idx < 0 or idx >= len(TEACHERS):
        idx = 0
    t = TEACHERS[idx]

    _username  = st.session_state.get("username","").lower()
    _is_admin  = _username in {"mim.ynu","mamunur rashid (admin)"}
    _is_self   = _username == t["photo_key"]
    _can_photo = _is_admin or _is_self

    photo_src = _get_photo_src(t["photo_key"])

    # ── Back button ──
    if st.button("← Back to Teacher List", key="td_back"):
        st.session_state.active_page = "Teacher Profile"
        st.rerun()

    st.markdown("""
    <style>
    .td-hero {
        background:linear-gradient(160deg,rgba(14,165,233,.12) 0%,rgba(99,102,241,.08) 50%,rgba(6,12,26,.99) 100%);
        border:1px solid rgba(56,189,248,.15); border-radius:28px;
        padding:40px; margin-bottom:24px; display:flex; gap:36px; align-items:flex-start;
    }
    .td-photo-wrap { flex-shrink:0; text-align:center; }
    .td-photo {
        width:160px; height:160px; border-radius:20px; object-fit:cover;
        border:3px solid rgba(56,189,248,.4);
        box-shadow:0 8px 32px rgba(14,165,233,.25);
    }
    .td-photo-ph {
        width:160px; height:160px; border-radius:20px; flex-shrink:0;
        background:linear-gradient(135deg,#0ea5e9,#6366f1);
        display:flex; align-items:center; justify-content:center;
        font-size:56px; font-weight:900; color:#fff;
        border:3px solid rgba(56,189,248,.4);
        box-shadow:0 8px 32px rgba(99,102,241,.25);
    }
    .td-name  { font-size:32px; font-weight:900; color:#f1f5f9; margin-bottom:4px; letter-spacing:-.5px; }
    .td-cn    { font-size:18px; color:#38bdf8; margin-bottom:6px; font-weight:600; }
    .td-role  { font-size:14px; color:#64748b; margin-bottom:20px; }
    .td-chips { display:flex; gap:8px; flex-wrap:wrap; margin-bottom:0; }
    .td-chip  {
        background:rgba(56,189,248,.10); border:1px solid rgba(56,189,248,.20);
        border-radius:20px; padding:4px 14px; font-size:12px; color:#7dd3fc; font-weight:600;
    }
    .td-grid  { display:grid; grid-template-columns:1fr 1fr; gap:16px; margin-bottom:24px; }
    .td-box   {
        background:rgba(10,18,36,.97); border:1px solid rgba(255,255,255,.07);
        border-radius:18px; padding:20px;
    }
    .td-box-label { font-size:10px; font-weight:800; color:#475569; text-transform:uppercase;
        letter-spacing:.10em; margin-bottom:6px; }
    .td-box-val   { font-size:15px; color:#e2e8f0; font-weight:600; }
    .td-box-sub   { font-size:12px; color:#64748b; margin-top:4px; }
    .td-photo-section {
        background:rgba(10,18,36,.97); border:1px solid rgba(245,158,11,.20);
        border-radius:18px; padding:22px; margin-bottom:24px;
    }
    .td-photo-label { font-size:10px; font-weight:800; color:#f59e0b; text-transform:uppercase;
        letter-spacing:.10em; margin-bottom:14px; }
    </style>
    """, unsafe_allow_html=True)

    # ── Hero card ──
    ph_html = f'<img src="{photo_src}" class="td-photo" width="160" height="160" style="width:160px;height:160px;object-fit:cover;border-radius:20px;flex-shrink:0;">' if photo_src else f'<div class="td-photo-ph">{t["initials"]}</div>'
    st.markdown(f"""
    <div class="td-hero">
        <div class="td-photo-wrap">
            {ph_html}
        </div>
        <div style="flex:1;">
            <div class="td-name">{t["name"]}</div>
            <div class="td-cn">{t["cn"]}</div>
            <div class="td-role">{t["role"]}</div>
            <div class="td-chips">
                <span class="td-chip">📚 {t["course"]}</span>
                <span class="td-chip">🔬 {t["research"].split(",")[0].strip()}</span>
                <span class="td-chip">🏛️ Yunnan University</span>
            </div>
        </div>
    </div>
    """, unsafe_allow_html=True)

    # ── Info grid ──
    st.markdown(f"""
    <div class="td-grid">
        <div class="td-box">
            <div class="td-box-label">Course</div>
            <div class="td-box-val">{t["course"]}</div>
        </div>
        <div class="td-box">
            <div class="td-box-label">Email</div>
            <div class="td-box-val">{t["email"]}</div>
        </div>
        <div class="td-box" style="grid-column:span 2;">
            <div class="td-box-label">Research Interests</div>
            <div class="td-box-val">{t["research"]}</div>
        </div>
        <div class="td-box">
            <div class="td-box-label">University</div>
            <div class="td-box-val">Yunnan University</div>
            <div class="td-box-sub">云南大学</div>
        </div>
        <div class="td-box">
            <div class="td-box-label">Campus</div>
            <div class="td-box-val">Chenggong Campus</div>
            <div class="td-box-sub">Kunming, Yunnan, China</div>
        </div>
    </div>
    """, unsafe_allow_html=True)

    # ── Photo management (teacher self OR admin) ──
    if _can_photo:
        label = "Your Profile Photo" if _is_self else f"Profile Photo -- {t['name']}"
        st.markdown(f"""
        <div class="td-photo-section">
            <div class="td-photo-label">{label}</div>
        </div>
        """, unsafe_allow_html=True)

        # Reload photo_src fresh (bypass session cache) so Remove button shows correctly
        _pk = t["photo_key"]
        _fresh_src = _get_photo_src(_pk)
        has_photo = _fresh_src is not None

        # Upload counter key — increments after each save to reset file uploader
        _up_count = st.session_state.get(f"_upc_{_pk}", 0)

        if has_photo:
            # Show current photo + Change/Remove buttons
            st.markdown(f"""
            <div style="display:flex;align-items:center;gap:16px;margin-bottom:12px;">
              <img src="{_fresh_src}" style="width:80px;height:80px;object-fit:cover;
                   border-radius:12px;border:2px solid rgba(56,189,248,.4);">
              <span style="color:rgba(255,255,255,.55);font-size:13px;">Current photo</span>
            </div>""", unsafe_allow_html=True)
            _col_up, _col_rm = st.columns([3, 1])
            with _col_up:
                up = st.file_uploader("Change Photo", type=["jpg","jpeg","png","webp"],
                                      key=f"td_upload_{_pk}_{_up_count}")
            with _col_rm:
                st.markdown("<div style='height:28px'></div>", unsafe_allow_html=True)
                if st.button("🗑 Remove", key=f"td_remove_{_pk}", use_container_width=True):
                    photos_dir = _pl.Path("photos")
                    for _e2 in ("jpg","jpeg","png","webp"):
                        _fp2 = photos_dir / f"{_pk}.{_e2}"
                        if _fp2.exists(): _fp2.unlink()
                    _delete_photo_sb(_pk)
                    st.session_state.pop(f"_sbp_{_pk}", None)
                    st.session_state[f"_upc_{_pk}"] = _up_count + 1
                    st.rerun()
        else:
            up = st.file_uploader("Upload Profile Photo", type=["jpg","jpeg","png","webp"],
                                  key=f"td_upload_{_pk}_{_up_count}")

        if up is not None:
            try:
                checked = validate_upload(up.name, up.getvalue(), PROFILE_IMAGE_POLICY)
                img_bytes = checked.data
                ext = "jpg" if checked.extension in {".jpg", ".jpeg"} else checked.extension.lstrip(".")
                photos_dir = _pl.Path("photos")
                photos_dir.mkdir(parents=True, exist_ok=True)
                for _e2 in ("jpg","jpeg","png","webp"):
                    _fp2 = photos_dir / f"{_pk}.{_e2}"
                    if _fp2.exists(): _fp2.unlink()
                (photos_dir / f"{_pk}.{ext}").write_bytes(img_bytes)
                saved_ok, _err = _save_photo_sb(_pk, img_bytes, ext)
                st.session_state.pop(f"_sbp_{_pk}", None)
                st.session_state[f"_upc_{_pk}"] = _up_count + 1
                if saved_ok:
                    st.success("✅ Photo saved permanently!")
                else:
                    st.error(f"❌ Save failed: `{_err}`")
                st.rerun()
            except ValueError as exc:
                st.error(str(exc))

    # ── Navigate between teachers ──
    st.markdown("<hr style='border-color:rgba(255,255,255,.06);margin:28px 0 20px;'>", unsafe_allow_html=True)
    nav1, nav2, nav3 = st.columns([1,2,1])
    with nav1:
        if idx > 0:
            prev = TEACHERS[idx-1]
            if st.button(f"← {prev['name']}", key="td_prev", use_container_width=True):
                st.session_state.tp_detail_idx = idx - 1
                st.rerun()
    with nav2:
        if st.button("View All Teachers", key="td_all", use_container_width=True):
            st.session_state.active_page = "Teacher Profile"
            st.rerun()
    with nav3:
        if idx < len(TEACHERS) - 1:
            nxt = TEACHERS[idx+1]
            if st.button(f"{nxt['name']} →", key="td_next", use_container_width=True):
                st.session_state.tp_detail_idx = idx + 1
                st.rerun()

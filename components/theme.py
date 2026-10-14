"""
components/theme.py — look & feel: colours, CSS, brand constants and image helpers.

Everything here is *presentation only*.  Pages call :func:`inject_theme` once per run.
"""

from __future__ import annotations

import base64
from pathlib import Path

import streamlit as st

APP_NAME = "Preluma"
APP_VERSION = "5.1"
TAGLINE = "Light Up Before Class"

TEAM_MEMBERS = [
    ("MAMUNUR RASHID", "Core Development · UI/UX · Integration · Deployment"),
    ("MD FAHIM", "Feature Logic · Quiz Testing · Interaction Feedback"),
    ("MD JIARUL ISLAM", "Topic Data · Documentation · Presentation Support"),
]

PROJECT_ROOT = Path(__file__).resolve().parents[1]
CAMPUS_IMAGE = PROJECT_ROOT / "assets" / "ynu_campus.jpg"
TEAM_IMAGE = PROJECT_ROOT / "assets" / "team_preluma.jpg"
SIDEBAR_IMAGE = PROJECT_ROOT / "assets" / "sidebar_bg.jpg"

# Design tokens used by the new dashboards and the Plotly charts.
PALETTE = {
    "bg": "#0b1220", "card": "rgba(15,23,42,.72)", "border": "rgba(148,163,184,.16)",
    "text": "#e2e8f0", "muted": "#94a3b8",
    "primary": "#38bdf8", "accent": "#818cf8", "good": "#34d399", "warn": "#fbbf24", "bad": "#f87171",
}


@st.cache_data(show_spinner=False)
def image_data_uri(path_str: str) -> str:
    """Return a ``data:`` URI for an image file ("" when the file is missing)."""
    path = Path(path_str)
    if not path.exists():
        return ""
    suffix = path.suffix.lower().lstrip(".")
    mime = "jpeg" if suffix in ("jpg", "jpeg") else "png"
    return f"data:image/{mime};base64,{base64.b64encode(path.read_bytes()).decode('ascii')}"


CAMPUS_URI = image_data_uri(str(CAMPUS_IMAGE))
TEAM_URI = image_data_uri(str(TEAM_IMAGE))
SIDEBAR_URI = image_data_uri(str(SIDEBAR_IMAGE))

CSS = """
<style>
/* System font stack -- no external CDN required, works offline */
*, *::before, *::after { box-sizing: border-box; }
html, body, [class*="css"] { font-family: ui-sans-serif, system-ui, -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif; }
.block-container { max-width: 100% !important; padding-top: 1.5rem !important; padding-left: 2.5rem !important; padding-right: 2.5rem !important; }
[data-testid="stSidebar"] { background: #03080f; border-right: 1px solid rgba(255,255,255,.06); }
[data-testid="stSidebar"] * { color: #e2e8f0; }
h1, h2, h3 { letter-spacing: -0.02em; }

/* ── Hero ── */
.hero {
    position: relative; min-height: 340px; border-radius: 28px;
    overflow: hidden; border: 1px solid rgba(255,255,255,.10);
    box-shadow: 0 32px 80px rgba(0,0,0,.55); margin-bottom: 2rem;
    background-size: cover; background-position: center 35%;
}
.hero-overlay {
    position: absolute; inset: 0;
    background:
        linear-gradient(105deg, rgba(2,6,23,.92) 0%, rgba(7,14,35,.78) 38%,
        rgba(15,23,62,.55) 65%, rgba(55,10,120,.40) 100%),
        radial-gradient(ellipse at 15% 50%, rgba(56,189,248,.18) 0%, transparent 50%);
}
.hero-content {
    position: relative; z-index: 2; padding: 44px 52px;
    display: flex; flex-direction: column; justify-content: center; min-height: 340px;
}
.hero-top { display: flex; align-items: center; gap: 12px; margin-bottom: 24px; }
.logo-mark {
    width: 44px; height: 44px; border-radius: 14px; flex-shrink: 0;
    background: linear-gradient(135deg, #38bdf8 0%, #818cf8 50%, #a78bfa 100%);
    box-shadow: 0 8px 24px rgba(56,189,248,.30);
    display: flex; align-items: center; justify-content: center;
}
.logo-mark svg { width: 22px; height: 22px; }
.brand-name { font-size: 17px; font-weight: 800; color: #fff; }
.brand-tag  { font-size: 12px; color: #93c5fd; margin-top: 1px; }
.uni-pill {
    margin-left: auto; padding: 6px 14px; border-radius: 999px;
    background: rgba(255,255,255,.10); border: 1px solid rgba(255,255,255,.20);
    color: #e2e8f0; font-size: 12px; font-weight: 600;
}
.ai-pill {
    padding: 6px 12px; border-radius: 999px; margin-left: 8px;
    background: rgba(52,211,153,.12); border: 1px solid rgba(52,211,153,.25);
    color: #6ee7b7; font-size: 11px; font-weight: 700;
}
.hero-badge {
    display: inline-flex; align-items: center; gap: 6px;
    padding: 7px 14px; border-radius: 999px; margin-bottom: 18px;
    background: rgba(56,189,248,.15); border: 1px solid rgba(56,189,248,.35);
    color: #7dd3fc; font-size: 11px; font-weight: 700; letter-spacing: .05em; text-transform: uppercase;
}
.hero-badge::before { content: ""; width: 6px; height: 6px; border-radius: 50%; background: #38bdf8; }
.hero h1 {
    font-size: 42px; line-height: 1.06; font-weight: 900; color: #fff;
    margin: 0 0 16px; letter-spacing: -.025em; max-width: 780px;
    text-shadow: 0 2px 30px rgba(0,0,0,.50);
}
.hero h1 span { color: #7dd3fc; }
.hero-sub { font-size: 16px; color: #cbd5e1; line-height: 1.65; max-width: 640px; }
.hero-stats { display: flex; gap: 32px; margin-top: 28px; }
.hero-stat-num { font-size: 22px; font-weight: 800; color: #fff; }
.hero-stat-lbl { font-size: 11px; color: #94a3b8; margin-top: 2px; font-weight: 500; }

/* ── Progress ── */
.progress-wrap {
    display: flex; gap: 0; margin: 8px 0 2rem;
    background: rgba(15,23,42,.60); border-radius: 16px;
    padding: 6px; border: 1px solid rgba(255,255,255,.07);
    overflow-x: auto;
}
.progress-step {
    flex: 1; min-width: 90px; text-align: center; padding: 10px 6px; border-radius: 12px;
    font-size: 11px; font-weight: 600; color: #64748b; white-space: nowrap;
}
.progress-step.done   { color: #34d399; background: rgba(52,211,153,.10); }
.progress-step.active { color: #38bdf8; background: rgba(56,189,248,.12); font-weight: 800; }

/* ── Section header ── */
.sec-head { display: flex; align-items: center; gap: 12px; margin: 2rem 0 1rem; }
.sec-icon {
    width: 36px; height: 36px; border-radius: 10px; flex-shrink: 0;
    display: flex; align-items: center; justify-content: center; font-size: 16px;
}
.sec-title { font-size: 20px; font-weight: 800; color: #f1f5f9; }
.sec-sub   { font-size: 13px; color: #64748b; margin-top: 2px; }

/* ── Cards ── */
.card-glass {
    background: rgba(15,23,42,.70); border: 1px solid rgba(255,255,255,.08);
    border-radius: 20px; padding: 20px 22px; margin: 10px 0;
}
.card-glass:hover { border-color: rgba(56,189,248,.22); }
.albl { font-size: 11px; font-weight: 700; letter-spacing: .08em; text-transform: uppercase; margin-bottom: 8px; }
.atxt { font-size: 15px; color: #e2e8f0; line-height: 1.7; }
.lbl-blue   { color: #60a5fa; }
.lbl-purple { color: #a78bfa; }
.lbl-green  { color: #34d399; }
.lbl-orange { color: #fb923c; }
.lbl-red    { color: #f87171; }
.lbl-yellow { color: #fbbf24; }
.lbl-cyan   { color: #22d3ee; }

/* ── AI bar ── */
.ai-bar {
    display: flex; align-items: center; gap: 10px; padding: 12px 16px;
    border-radius: 14px; margin-bottom: 16px;
    background: rgba(52,211,153,.08); border: 1px solid rgba(52,211,153,.25);
}
.ai-dot { width: 8px; height: 8px; border-radius: 50%; background: #34d399; box-shadow: 0 0 8px #34d399; }
.ai-txt { font-size: 13px; color: #6ee7b7; font-weight: 600; }

/* ── Notice ── */
.notice {
    padding: 13px 16px; border-radius: 14px; margin-bottom: 14px;
    background: rgba(56,189,248,.08); border: 1px solid rgba(56,189,248,.20);
    color: #bae6fd; font-size: 14px; line-height: 1.6;
}

/* ── Score ── */
.score-big { font-size: 56px; font-weight: 900; line-height: 1; }
.score-lbl { font-size: 14px; color: #94a3b8; margin-top: 6px; }
.r-pill { display: inline-block; padding: 6px 18px; border-radius: 999px; font-size: 14px; font-weight: 700; margin-top: 8px; }
.pill-g { background: rgba(52,211,153,.15); color: #34d399; border: 1px solid rgba(52,211,153,.30); }
.pill-y { background: rgba(251,191,36,.15);  color: #fbbf24; border: 1px solid rgba(251,191,36,.30); }
.pill-r { background: rgba(248,113,113,.15); color: #f87171; border: 1px solid rgba(248,113,113,.30); }

/* ── KPI ── */
.kpi-grid { display: grid; grid-template-columns: repeat(4,1fr); gap: 14px; margin: 1.5rem 0; }
.kpi-card {
    background: rgba(15,23,42,.70); border: 1px solid rgba(255,255,255,.07);
    border-radius: 18px; padding: 20px 18px;
}
.kpi-num { font-size: 30px; font-weight: 900; color: #fff; }
.kpi-lbl { font-size: 11px; font-weight: 700; color: #64748b; text-transform: uppercase; letter-spacing: .07em; margin-top: 6px; }

/* ── Flow ── */
.flow-grid { display: grid; grid-template-columns: repeat(3,1fr); gap: 16px; margin: 1.5rem 0; }
.flow-card {
    background: rgba(15,23,42,.60); border: 1px solid rgba(255,255,255,.07);
    border-radius: 18px; padding: 22px 20px;
}
.flow-step  { font-size: 11px; font-weight: 700; color: #38bdf8; letter-spacing: .08em; text-transform: uppercase; margin-bottom: 10px; }
.flow-title { font-size: 18px; font-weight: 800; color: #f1f5f9; margin-bottom: 8px; }
.flow-desc  { font-size: 14px; color: #94a3b8; line-height: 1.6; }

/* ── Evidence ── */
.ev-grid { display: grid; grid-template-columns: repeat(3,1fr); gap: 14px; margin: 1.5rem 0; }
.ev-card {
    background: linear-gradient(135deg, rgba(14,165,233,.10), rgba(124,58,237,.08));
    border: 1px solid rgba(125,211,252,.15); border-radius: 18px; padding: 18px 16px;
}
.ev-card h4 { font-size: 15px; font-weight: 700; color: #e2e8f0; margin: 0 0 8px; }
.ev-card p  { font-size: 13px; color: #94a3b8; line-height: 1.6; margin: 0; }

/* ── Rubric ── */
.rubric-grid { display: grid; grid-template-columns: repeat(2,1fr); gap: 14px; margin: 1.5rem 0; }
.rubric-card {
    padding: 18px; border-radius: 22px;
    background: linear-gradient(135deg, rgba(34,197,94,.12), rgba(14,165,233,.10));
    border: 1px solid rgba(125,211,252,.22);
}
.rubric-card h4 { color: #fff; margin: 0 0 8px; font-size: 16px; }
.rubric-card p  { color: #cbd5e1; margin: 0; line-height: 1.55; font-size: 14px; }

/* ── Team ── */
.member-grid { display: grid; grid-template-columns: repeat(3,1fr); gap: 16px; margin: 1.5rem 0; }
.member-card {
    padding: 20px; border-radius: 24px;
    background: linear-gradient(135deg, rgba(15,23,42,.94), rgba(30,41,59,.82));
    border: 1px solid rgba(125,211,252,.18);
}
/* Equal styling for all team members -- no visual hierarchy */
.member-role { color: #93c5fd; font-weight: 900; font-size: 11px; letter-spacing: .08em; text-transform: uppercase; margin-bottom: 8px; }
.member-card h3 { color: #fff; margin: 0 0 8px; font-size: 19px; }
.member-card p  { color: #cbd5e1; line-height: 1.55; margin: 0; font-size: 14px; }
.contrib-list { margin-top: 10px; padding-left: 16px; color: #94a3b8; font-size: 13px; }
.contrib-list li { margin-bottom: 5px; }

/* ── Chip ── */
.chip-row { display: flex; flex-wrap: wrap; gap: 8px; margin: 1rem 0 1.5rem; }
.chip { padding: 7px 14px; border-radius: 999px; background: rgba(99,102,241,.12); border: 1px solid rgba(99,102,241,.25); color: #a5b4fc; font-size: 12px; font-weight: 600; }

/* ── Concept ── */
.concept-block {
    background: rgba(15,23,42,.55); border: 1px solid rgba(255,255,255,.07);
    border-radius: 16px; padding: 16px 18px; margin: 8px 0;
}
.concept-block-title { font-size: 11px; font-weight: 700; letter-spacing: .08em; text-transform: uppercase; margin-bottom: 8px; color: #818cf8; }
.concept-block p { font-size: 14px; color: #cbd5e1; line-height: 1.65; margin: 3px 0; }

/* ── Sidebar team ── */
.team-box { background: rgba(15,23,42,.80); border: 1px solid rgba(255,255,255,.07); border-radius: 16px; padding: 14px 16px; margin-top: 16px; }
.team-ttl { font-size: 10px; font-weight: 800; color: #475569; letter-spacing: .10em; text-transform: uppercase; margin-bottom: 12px; }
.team-row { padding: 9px 0; border-bottom: 1px solid rgba(255,255,255,.05); }
.team-row:last-child { border-bottom: none; }
.team-name { font-size: 12px; font-weight: 700; color: #e2e8f0; }
.team-role { font-size: 11px; color: #475569; margin-top: 2px; }

/* ── Buttons ── */
.stButton > button {
    border-radius: 14px !important; font-weight: 700 !important; font-size: 14px !important;
    min-height: 50px !important; border: none !important;
    background: linear-gradient(135deg, #2563eb, #7c3aed) !important;
    color: #fff !important; box-shadow: 0 4px 20px rgba(37,99,235,.35) !important;
}
.stButton > button:hover { opacity: .88 !important; }
/* Secondary buttons -- minimal ghost (overrides gradient above via attribute specificity) */
.stButton > button[data-testid="baseButton-secondary"] {
    background: rgba(255,255,255,.04) !important;
    border: 1px solid rgba(255,255,255,.10) !important;
    color: #94a3b8 !important;
    min-height: 38px !important;
    font-size: 12px !important;
    font-weight: 600 !important;
    letter-spacing: .03em !important;
    border-radius: 10px !important;
    box-shadow: none !important;
}
.stButton > button[data-testid="baseButton-secondary"]:hover {
    background: rgba(255,255,255,.07) !important;
    border-color: rgba(255,255,255,.18) !important;
    color: #e2e8f0 !important;
    opacity: 1 !important;
}
/* Expanders -- minimal card rows (main content only, not sidebar) */
[data-testid="stMain"] [data-testid="stExpander"] {
    border: 1px solid rgba(255,255,255,.07) !important;
    border-radius: 12px !important;
    background: rgba(255,255,255,.018) !important;
    box-shadow: none !important;
    margin-bottom: 5px !important;
}
[data-testid="stMain"] [data-testid="stExpanderToggleIcon"],
[data-testid="stMain"] [data-testid="stExpander"] summary {
    padding: 12px 16px !important;
    font-size: 14px !important;
    font-weight: 650 !important;
    color: #e2e8f0 !important;
    letter-spacing: -.005em !important;
    border-radius: 12px !important;
}
[data-testid="stMain"] [data-testid="stExpanderToggleIcon"]:hover,
[data-testid="stMain"] [data-testid="stExpander"] summary:hover {
    background: rgba(255,255,255,.03) !important;
}
[data-testid="stMain"] [data-testid="stExpanderDetails"] {
    border-top: 1px solid rgba(255,255,255,.05) !important;
    padding: 14px 16px 16px !important;
}

@media(max-width:900px) {
    .kpi-grid,.flow-grid,.ev-grid,.rubric-grid,.member-grid { grid-template-columns: 1fr; }
    .hero-content { padding: 28px 24px; }
    .hero h1 { font-size: 28px; }
    .hero-stats { gap: 20px; }
}

/* ── Team photo: full image, no face cropping ── */
.team-photo-hero { position:relative; width:100%; aspect-ratio:16/9; border-radius:30px; overflow:hidden; background-size:100% auto; background-position:center; background-repeat:no-repeat; background-color:#020617; border:1px solid rgba(125,211,252,.25); box-shadow:0 28px 70px rgba(0,0,0,.42); margin:1rem 0 1.75rem; }
.team-photo-hero::after { content:''; position:absolute; inset:0; background:linear-gradient(0deg,rgba(2,6,23,.90) 0%,rgba(2,6,23,.18) 48%,rgba(2,6,23,.12) 100%),linear-gradient(90deg,rgba(14,165,233,.12),rgba(124,58,237,.14)); }
.team-photo-content { position:absolute; z-index:2; left:34px; right:34px; bottom:30px; }
.team-photo-content h1 { color:#fff; font-size:38px; line-height:1.12; margin:12px 0 8px; text-shadow:0 4px 24px rgba(0,0,0,.65); }
.team-photo-content p { color:#e2e8f0; max-width:760px; line-height:1.55; margin:0; text-shadow:0 3px 18px rgba(0,0,0,.65); }
.sidebar-profile { padding:12px 14px; border-radius:16px; background:rgba(15,23,42,.72); border:1px solid rgba(148,163,184,.12); margin:.35rem 0 1rem; }
.sidebar-profile b { color:#f8fafc; font-size:13px; }
.sidebar-profile span { color:#94a3b8; font-size:12px; }
.nav-label { color:#64748b; font-size:10px; font-weight:900; letter-spacing:.14em; text-transform:uppercase; margin:16px 0 7px; }
.ai-main-answer { padding:22px 24px; border-radius:22px; background:linear-gradient(135deg,rgba(15,23,42,.97),rgba(30,41,59,.88)); border:1px solid rgba(99,102,241,.30); box-shadow:0 18px 45px rgba(2,6,23,.26); color:#e5e7eb; font-size:16px; line-height:1.75; white-space:pre-wrap; }
.ai-meta { color:#94a3b8; font-size:12px; margin:7px 0 12px; }
.follow-grid { display:flex; flex-wrap:wrap; gap:8px; margin:12px 0; }
@media (max-width:900px){ .team-photo-content h1{font-size:28px}.team-photo-content{left:22px;right:22px;bottom:22px}.team-photo-hero{aspect-ratio:4/3;background-size:cover;} }
.provider-grid { display:grid; grid-template-columns: repeat(3,1fr); gap:10px; margin: 10px 0 18px; }
.provider-card { background:rgba(15,23,42,.72); border:1px solid rgba(255,255,255,.08); border-radius:14px; padding:12px 14px; }
.provider-name { color:#e2e8f0; font-size:13px; font-weight:700; }
.provider-status { color:#34d399; font-size:11px; margin-top:4px; }
.chat-user { margin:14px 0 10px auto; max-width:80%; background:linear-gradient(135deg,#2563eb,#7c3aed); color:white; padding:14px 16px; border-radius:18px 18px 4px 18px; line-height:1.55; }
.chat-ai { margin:10px auto 16px 0; max-width:92%; background:rgba(15,23,42,.78); border:1px solid rgba(125,211,252,.18); padding:16px 18px; border-radius:18px 18px 18px 4px; }
.context-chip { display:inline-block; padding:7px 12px; border-radius:999px; background:rgba(56,189,248,.10); border:1px solid rgba(56,189,248,.25); color:#7dd3fc; font-size:12px; font-weight:700; margin:0 8px 8px 0; }
@media (max-width: 900px) { .provider-grid { grid-template-columns: 1fr; } }


/* ─────────────────────────────────────────────────────────────────────
   V25 DESIGN SYSTEM
   No emoji, compact sidebar, page-specific interface identities.
   ───────────────────────────────────────────────────────────────────── */
html, body, [class*="css"] {
    font-family: Inter, ui-sans-serif, system-ui, -apple-system, BlinkMacSystemFont,
                 "Segoe UI", sans-serif;
}
h1, h2, h3, .page-title, .sec-title {
    font-family: Manrope, Inter, ui-sans-serif, system-ui, sans-serif;
}
code, pre, [data-testid="stCodeBlock"] {
    font-family: "SFMono-Regular", Consolas, "Liberation Mono", monospace;
}

/* ── SIDEBAR -- Tower night photo background, ultra-clean ── */
[data-testid="stSidebar"] {
    background-color: #020810;
    border-right: 1px solid rgba(148,163,184,.08);
    position: relative;
    overflow: hidden;
}
/* Tower photo injected via JS below */
[data-testid="stSidebar"] > div:first-child {
    padding-top: 0 !important;
    position: relative;
    z-index: 2;
}
/* Nav buttons -- ghost style, left-aligned */
[data-testid="stSidebar"] .stButton > button {
    min-height: 40px !important;
    border-radius: 10px !important;
    justify-content: flex-start !important;
    padding: .52rem .82rem !important;
    background: rgba(8,14,26,.55) !important;
    border: 1px solid rgba(255,255,255,.06) !important;
    box-shadow: none !important;
    color: rgba(203,213,225,.85) !important;
    font-weight: 500 !important;
    font-size: 13.5px !important;
    letter-spacing: .01em;
    backdrop-filter: blur(6px);
    transition: background .15s ease, border-color .15s ease, color .15s ease, transform .12s ease;
}
[data-testid="stSidebar"] .stButton > button:hover {
    background: rgba(56,189,248,.12) !important;
    border-color: rgba(56,189,248,.28) !important;
    color: #e0f2fe !important;
    transform: translateX(3px);
}
[data-testid="stSidebar"] .stButton > button:active {
    background: rgba(56,189,248,.22) !important;
}
/* Active page -- primary type button */
[data-testid="stSidebar"] .stButton > button[data-testid="baseButton-primary"] {
    background: rgba(56,189,248,.18) !important;
    border-color: rgba(56,189,248,.40) !important;
    color: #bae6fd !important;
    font-weight: 600 !important;
}
/* Sidebar expanders (LEARN/TEACH) -- strip card border */
[data-testid="stSidebar"] [data-testid="stExpander"],
[data-testid="stSidebar"] details {
    border: none !important;
    background: transparent !important;
    box-shadow: none !important;
    border-radius: 0 !important;
    margin-bottom: 0 !important;
}
[data-testid="stSidebar"] details summary,
[data-testid="stSidebar"] [data-testid="stExpander"] summary {
    padding: 6px 4px 4px !important;
    font-size: 10px !important;
    font-weight: 800 !important;
    letter-spacing: .12em !important;
    color: #b9cde2 !important;
    background: transparent !important;
    list-style: none !important;
}
[data-testid="stSidebar"] details summary::-webkit-details-marker { display: none; }
[data-testid="stSidebar"] [data-testid="stExpanderToggleIcon"] { display: none !important; }
[data-testid="stSidebar"] [data-testid="stExpanderDetails"] {
    border-top: none !important;
    padding: 2px 0 4px !important;
}
/* Keep widget labels available to sighted and assistive-technology users. */
[data-testid="stSidebar"] .stTextInput input {
    background: rgba(8,14,26,.7) !important;
    border: 1px solid rgba(255,255,255,.10) !important;
    border-radius: 10px !important;
    color: #e2e8f0 !important;
    font-size: 13px !important;
    padding: .45rem .72rem !important;
    backdrop-filter: blur(8px);
}
[data-testid="stSidebar"] .stTextInput input::placeholder { color: #4a5568 !important; }
[data-testid="stSidebar"] .stTextInput input:focus {
    border-color: rgba(56,189,248,.40) !important;
    box-shadow: 0 0 0 2px rgba(56,189,248,.12) !important;
}
/* Hide Streamlit's toggle label clutter */
[data-testid="stSidebar"] .stToggle { display: none !important; }
/* Version caption */
[data-testid="stSidebar"] .stCaptionContainer { opacity: .35; }

/* Nav section labels */
.nav-label {
    margin: 1.1rem 0 .3rem .04rem;
    color: #b9cde2 !important;
    font-size: 9.5px !important;
    letter-spacing: .2em;
    font-weight: 800;
    text-transform: uppercase;
}

/* Sidebar top branding panel -- sits above the photo */
.sb-brand {
    padding: 22px 16px 14px;
    background: linear-gradient(180deg, rgba(2,8,16,.96) 0%, rgba(2,8,16,.70) 100%);
    border-bottom: 1px solid rgba(255,255,255,.06);
    margin-bottom: 4px;
}
.sb-brand-name {
    font-size: 22px;
    font-weight: 800;
    color: #fff;
    letter-spacing: -.02em;
    line-height: 1.1;
}
.sb-brand-tag {
    font-size: 11px;
    color: rgba(56,189,248,.70);
    letter-spacing: .05em;
    margin-top: 2px;
    font-weight: 500;
}

/* Student identity chip */
.sb-student-chip {
    display: flex;
    align-items: center;
    gap: 9px;
    background: rgba(8,14,26,.72);
    border: 1px solid rgba(56,189,248,.15);
    border-radius: 12px;
    padding: 9px 12px;
    margin: 6px 0 4px;
    backdrop-filter: blur(10px);
}
.sb-student-name { color: #f8fafc; font-weight: 700; font-size: 13.5px; }
.sb-student-sub  { color: #64748b; font-size: 11px; margin-top: 2px; }
.sb-dot { width: 8px; height: 8px; border-radius: 50%; background: #22d3ee; flex-shrink: 0; box-shadow: 0 0 6px rgba(34,211,238,.5); }

/* Unread badge */
.sb-badge {
    display: inline-block;
    background: rgba(239,68,68,.85);
    color: #fff;
    font-size: 10px;
    font-weight: 800;
    border-radius: 20px;
    padding: 1px 7px;
    margin-left: 6px;
    vertical-align: middle;
}

/* Sidebar bottom status pill */
.sb-status {
    margin: 12px 0 8px;
    padding: 10px 12px;
    border-radius: 12px;
    background: rgba(6,182,212,.06);
    border: 1px solid rgba(6,182,212,.14);
    backdrop-filter: blur(8px);
}
.sb-status-dot { display:inline-block; width:7px; height:7px; border-radius:50%; background:#10b981; margin-right:7px; box-shadow: 0 0 5px rgba(16,185,129,.6); }
.sb-status-text { color: rgba(167,243,208,.7); font-size: 11.5px; font-weight: 600; }

/* Sidebar nav area padding */
.sb-nav-wrap { padding: 0 10px 12px; }

/* reusable unique page header */
.page-intro {
    position: relative;
    overflow: hidden;
    border-radius: 26px;
    padding: 30px 34px;
    margin: 4px 0 24px;
    border: 1px solid var(--page-border);
    background:
        linear-gradient(120deg, var(--page-bg-a), var(--page-bg-b)),
        #0b1220;
    box-shadow: 0 22px 60px rgba(0,0,0,.26);
}
.page-intro::after {
    content: "";
    position: absolute; width: 260px; height: 260px; right:-90px; top:-125px;
    border-radius: 50%; background: var(--page-glow); filter: blur(4px);
}
.page-kicker {
    color: var(--page-accent); font-size: 11px; font-weight: 800;
    text-transform: uppercase; letter-spacing: .15em; margin-bottom: 10px;
}
.page-title {
    position: relative; z-index: 1; color:#f8fafc; font-size: 34px;
    line-height:1.12; letter-spacing:-.035em; font-weight:800; margin:0;
}
.page-subtitle {
    position:relative; z-index:1; max-width:760px; color:#9fb0c6;
    font-size:14px; line-height:1.7; margin-top:10px;
}
.theme-ai       { --page-accent:#c4b5fd; --page-border:rgba(139,92,246,.28); --page-bg-a:rgba(76,29,149,.32); --page-bg-b:rgba(15,23,42,.88); --page-glow:rgba(139,92,246,.18); }
.theme-homework { --page-accent:#fbbf24; --page-border:rgba(245,158,11,.25); --page-bg-a:rgba(120,53,15,.26); --page-bg-b:rgba(15,23,42,.9); --page-glow:rgba(245,158,11,.13); }
.theme-teacher  { --page-accent:#67e8f9; --page-border:rgba(6,182,212,.24); --page-bg-a:rgba(8,47,73,.52); --page-bg-b:rgba(15,23,42,.9); --page-glow:rgba(6,182,212,.14); }
.theme-student  { --page-accent:#a78bfa; --page-border:rgba(167,139,250,.25); --page-bg-a:rgba(49,15,122,.28); --page-bg-b:rgba(15,23,42,.92); --page-glow:rgba(167,139,250,.14); }
.theme-evidence { --page-accent:#86efac; --page-border:rgba(34,197,94,.25); --page-bg-a:rgba(5,46,22,.48); --page-bg-b:rgba(8,15,27,.95); --page-glow:rgba(34,197,94,.13); }
.theme-defense  { --page-accent:#bfdbfe; --page-border:rgba(96,165,250,.25); --page-bg-a:rgba(30,58,138,.30); --page-bg-b:rgba(15,23,42,.93); --page-glow:rgba(59,130,246,.15); }
.theme-demo     { --page-accent:#fdba74; --page-border:rgba(249,115,22,.24); --page-bg-a:rgba(124,45,18,.28); --page-bg-b:rgba(15,23,42,.92); --page-glow:rgba(249,115,22,.12); }
.theme-roadmap  { --page-accent:#e9d5ff; --page-border:rgba(168,85,247,.24); --page-bg-a:rgba(88,28,135,.30); --page-bg-b:rgba(15,23,42,.92); --page-glow:rgba(168,85,247,.14); }

/* distinct workspace panels */
.assignment-card {
    border:1px solid rgba(245,158,11,.21);
    background:linear-gradient(145deg,rgba(41,30,14,.72),rgba(12,18,29,.92));
    border-radius:20px;padding:20px 22px;margin:12px 0;
}
.analytics-panel {
    border:1px solid rgba(6,182,212,.18);
    background:linear-gradient(145deg,rgba(8,47,73,.34),rgba(11,18,32,.94));
    border-radius:20px;padding:18px;
}
.lab-panel {
    border:1px solid rgba(34,197,94,.18);
    background:#07110d;border-radius:18px;padding:18px;
    box-shadow:inset 0 0 35px rgba(34,197,94,.025);
}
.defense-panel {
    border:1px solid rgba(96,165,250,.20);
    background:linear-gradient(155deg,rgba(30,58,138,.20),rgba(15,23,42,.92));
    border-radius:20px;padding:20px;
}

/* AI chat: real conversation layout */
.ai-chat-shell {
    max-width: 940px; margin: 0 auto; border:1px solid rgba(139,92,246,.18);
    background:linear-gradient(160deg,rgba(24,18,46,.78),rgba(8,14,25,.95));
    border-radius:24px;padding:18px 20px 22px;
}
.chat-user {
    width:fit-content; max-width:78%; margin:18px 0 10px auto !important;
    background:linear-gradient(135deg,#4f46e5,#7c3aed) !important;
    border:0 !important; border-radius:20px 20px 5px 20px !important;
    padding:13px 16px !important; color:white !important;
}
.ai-meta { color:#7d8ca5 !important; font-size:11px !important; margin:0 0 6px 5px !important; }
.ai-main-answer {
    max-width:92%; border:1px solid rgba(167,139,250,.18) !important;
    border-radius:5px 20px 20px 20px !important;
    background:rgba(17,24,39,.88) !important; padding:18px 20px !important;
    color:#dbe4f0 !important; font-size:15px !important; line-height:1.82 !important;
    white-space:pre-wrap;
}
.context-chip { background:rgba(139,92,246,.08) !important; border-color:rgba(167,139,250,.20) !important; }

/* premium team background hero; keeps full 16:9 composition */
.team-photo-hero {
    min-height: 500px !important;
    background-size: cover !important;
    background-position: center center !important;
    border-radius: 28px !important;
    border: 1px solid rgba(148,163,184,.18) !important;
    box-shadow: 0 30px 80px rgba(0,0,0,.42) !important;
}
.team-photo-hero::before {
    background:
        linear-gradient(90deg, rgba(2,6,23,.88) 0%, rgba(2,6,23,.52) 42%, rgba(2,6,23,.12) 72%, rgba(2,6,23,.18) 100%),
        linear-gradient(0deg, rgba(2,6,23,.62), transparent 52%) !important;
}
.team-photo-content { max-width: 575px !important; padding: 44px !important; }
.team-photo-content h1 { font-size: 38px !important; line-height:1.12 !important; }

/* reduce repeated oversized visual language */
.stButton > button {
    border-radius: 12px;
    font-weight: 650;
}
@media (max-width: 850px) {
    .page-intro { padding:24px 22px; border-radius:20px; }
    .page-title { font-size:28px; }
    .team-photo-hero { min-height:420px !important; background-position:center center !important; }
    .team-photo-content { padding:26px !important; }
}

/* Sidebar expander (collapsible sections) */
[data-testid="stSidebar"] [data-testid="stExpander"] {
    border: none !important;
    background: transparent !important;
}
[data-testid="stSidebar"] [data-testid="stExpander"] summary {
    padding: 8px 4px !important;
    font-size: 9.5px !important;
    font-weight: 800 !important;
    color: #b9cde2 !important;
    letter-spacing: .18em !important;
    text-transform: uppercase !important;
    border-radius: 8px !important;
    border: none !important;
    background: transparent !important;
}
[data-testid="stSidebar"] [data-testid="stExpander"] summary:hover {
    color: #f1f7ff !important;
    background: rgba(255,255,255,.03) !important;
}
[data-testid="stSidebar"] [data-testid="stExpander"] summary svg {
    color: rgba(100,116,139,.55) !important;
}
[data-testid="stSidebar"] [data-testid="stExpander"] > div:last-child {
    padding: 0 !important;
    border: none !important;
}

</style>
"""


DASHBOARD_CSS = """
<style>
.pl-grid{display:grid;gap:14px;margin:6px 0 18px}
.pl-grid.c4{grid-template-columns:repeat(4,minmax(0,1fr))}
.pl-grid.c3{grid-template-columns:repeat(3,minmax(0,1fr))}
.pl-grid.c2{grid-template-columns:repeat(2,minmax(0,1fr))}
@media(max-width:900px){.pl-grid.c4,.pl-grid.c3{grid-template-columns:repeat(2,minmax(0,1fr))}}
@media(max-width:560px){.pl-grid.c4,.pl-grid.c3,.pl-grid.c2{grid-template-columns:1fr}}
.pl-card{background:linear-gradient(160deg,rgba(15,23,42,.82),rgba(30,41,59,.62));border:1px solid rgba(148,163,184,.16);
  border-radius:16px;padding:16px 18px;box-shadow:0 10px 30px rgba(0,0,0,.28);backdrop-filter:blur(6px)}
.pl-card .lbl{font-size:11px;font-weight:800;letter-spacing:.12em;text-transform:uppercase;color:#94a3b8}
.pl-card .val{font-size:30px;font-weight:800;color:#f1f5f9;line-height:1.15;margin-top:4px}
.pl-card .sub{font-size:12.5px;color:#94a3b8;margin-top:4px}
.pl-card.good .val{color:#34d399}.pl-card.warn .val{color:#fbbf24}.pl-card.bad .val{color:#f87171}
.pl-bar{height:9px;border-radius:99px;background:rgba(148,163,184,.18);overflow:hidden;margin-top:8px}
.pl-bar>span{display:block;height:100%;border-radius:99px;background:linear-gradient(90deg,#38bdf8,#818cf8)}
.pl-bar.good>span{background:linear-gradient(90deg,#34d399,#22d3ee)}
.pl-bar.warn>span{background:linear-gradient(90deg,#fbbf24,#fb923c)}
.pl-bar.bad>span{background:linear-gradient(90deg,#f87171,#fb7185)}
.pl-step{display:flex;gap:12px;align-items:flex-start;padding:12px 14px;border-radius:14px;margin-bottom:10px;
  background:rgba(15,23,42,.6);border:1px solid rgba(148,163,184,.14)}
.pl-step .n{flex:0 0 30px;height:30px;border-radius:50%;display:flex;align-items:center;justify-content:center;
  font-weight:800;font-size:13px;color:#0b1220;background:#38bdf8}
.pl-step.revise .n{background:#f87171}.pl-step.practice .n{background:#fbbf24}.pl-step.next .n{background:#34d399}
.pl-step .t{font-weight:700;color:#f1f5f9;font-size:14.5px}
.pl-step .r{font-size:12.5px;color:#94a3b8;margin-top:2px}
.pl-pill{display:inline-block;padding:2px 10px;border-radius:99px;font-size:11px;font-weight:700;
  background:rgba(56,189,248,.14);color:#7dd3fc;margin-right:6px}
.pl-pill.good{background:rgba(52,211,153,.14);color:#6ee7b7}
.pl-pill.warn{background:rgba(251,191,36,.14);color:#fcd34d}
.pl-pill.bad{background:rgba(248,113,113,.14);color:#fca5a5}
.pl-badge{display:flex;gap:10px;align-items:center;padding:10px 12px;border-radius:12px;
  background:rgba(15,23,42,.6);border:1px solid rgba(148,163,184,.14)}
.pl-badge .ic{font-size:22px}.pl-badge .nm{font-weight:700;color:#e2e8f0;font-size:13.5px}
.pl-badge .ds{font-size:11.5px;color:#94a3b8}
.pl-src{font-size:12px;color:#94a3b8;border-left:3px solid #38bdf8;padding:4px 10px;margin:4px 0;background:rgba(15,23,42,.45)}
</style>
"""


UI_REFINEMENT_CSS = """
<style>
:root {
    --pl-bg: #020817;
    --pl-surface: rgba(9, 18, 36, .88);
    --pl-surface-raised: rgba(13, 25, 48, .94);
    --pl-border: rgba(148, 163, 184, .15);
    --pl-border-strong: rgba(125, 211, 252, .28);
    --pl-text: #f1f7ff;
    --pl-muted: #9eb0c7;
    --pl-cyan: #38bdf8;
    --pl-indigo: #818cf8;
    --pl-emerald: #34d399;
    --pl-amber: #fbbf24;
    --pl-rose: #fb7185;
    --pl-violet: #c084fc;
    --pl-radius-lg: 24px;
    --pl-radius-md: 16px;
    --pl-shadow: 0 24px 70px rgba(0, 0, 0, .34);
}

.stApp {
    background:
        radial-gradient(circle at 8% 18%, rgba(14, 165, 233, .07), transparent 28rem),
        radial-gradient(circle at 86% 70%, rgba(99, 102, 241, .06), transparent 34rem),
        var(--pl-bg) !important;
    color: var(--pl-text);
}
.block-container { max-width: 1480px !important; padding: 1.5rem 2.5rem 3rem !important; }
p, li { color: #c1cede; }

/* Accessible interaction states across the application. */
button:focus-visible, a:focus-visible, input:focus-visible, textarea:focus-visible,
[tabindex]:focus-visible, summary:focus-visible {
    outline: 3px solid rgba(56, 189, 248, .72) !important;
    outline-offset: 3px !important;
}
.stButton > button { transition: transform .16s ease, border-color .16s ease, background .16s ease !important; }
.stButton > button:hover { transform: translateY(-1px); opacity: 1 !important; }

/* Original illuminated tower image remains the sidebar's visual anchor. */
[data-testid="stSidebar"] { box-shadow: 16px 0 48px rgba(0, 0, 0, .22); }
[data-testid="stSidebar"] > div:first-child {
    background-position: 43% 52% !important;
    min-height: 100%;
}
.sb-brand {
    margin: 0 -10px 10px;
    padding: 24px 20px 18px;
    background: linear-gradient(180deg, rgba(2, 8, 18, .98), rgba(2, 8, 18, .76));
    border-bottom-color: rgba(125, 211, 252, .12);
}
.sb-brand-name { font-size: 24px; letter-spacing: -.035em; }
.sb-brand-tag { color: #54c8f7; letter-spacing: .08em; margin-top: 5px; }
.sb-student-chip {
    padding: 11px 12px; margin: 8px 0 12px;
    background: rgba(2, 8, 18, .74); border-color: rgba(125, 211, 252, .20);
    box-shadow: inset 0 1px rgba(255, 255, 255, .04), 0 10px 30px rgba(0, 0, 0, .18);
}
.sb-avatar {
    display: grid; place-items: center; width: 34px; height: 34px; flex: 0 0 34px;
    border-radius: 11px; color: #e0f2fe; font-size: 11px; font-weight: 900; letter-spacing: .04em;
    background: linear-gradient(145deg, rgba(14, 165, 233, .36), rgba(79, 70, 229, .34));
    border: 1px solid rgba(125, 211, 252, .25);
}
.sb-student-sub { color: #8da0b8; letter-spacing: .08em; text-transform: uppercase; font-size: 9.5px; font-weight: 800; }
.sb-status {
    margin-top: 14px; padding: 11px 12px; background: rgba(2, 12, 22, .74);
    border-color: rgba(52, 211, 153, .20); box-shadow: 0 10px 24px rgba(0, 0, 0, .16);
}
.sb-status.is-offline { border-color: rgba(251, 191, 36, .24); }
.sb-status.is-offline .sb-status-dot { background: var(--pl-amber); box-shadow: 0 0 8px rgba(251, 191, 36, .7); }
.sb-status.is-offline .sb-status-text { color: #fde68a; }
.sb-storage { color: #8293aa; font-size: 10.5px; margin-top: 5px; }
[data-testid="stSidebar"] .stButton > button { min-height: 42px !important; }
[data-testid="stSidebar"] .stButton > button[data-testid="baseButton-primary"] {
    box-shadow: inset 3px 0 #38bdf8, 0 8px 24px rgba(2, 132, 199, .10) !important;
}

/* Homepage hero — exact repository campus image supplied through --home-campus-image. */
.home-hero {
    position: relative; isolation: isolate; overflow: hidden; min-height: 510px;
    display: flex; align-items: stretch;
    margin: -1.5rem -2.5rem 0; border-bottom: 1px solid rgba(125, 211, 252, .16);
    background-image: var(--home-campus-image); background-size: cover; background-position: center 43%;
    box-shadow: 0 34px 80px rgba(0, 0, 0, .36);
}
.home-hero::before {
    content: ""; position: absolute; inset: 0; z-index: -1;
    background:
        linear-gradient(90deg, rgba(1, 7, 20, .97) 0%, rgba(2, 10, 27, .88) 36%, rgba(3, 12, 30, .48) 63%, rgba(2, 8, 20, .14) 100%),
        linear-gradient(0deg, rgba(2, 8, 23, .96) 0%, transparent 30%, rgba(2, 8, 23, .08) 100%);
}
.home-hero::after {
    content: ""; position: absolute; inset: 0; z-index: -1; pointer-events: none;
    background: radial-gradient(circle at 15% 48%, rgba(14, 165, 233, .14), transparent 28rem);
}
.home-hero-content {
    width: min(760px, 66%); padding: clamp(68px, 8vw, 118px) 4.5rem 72px;
    display: flex; flex-direction: column; justify-content: center;
}
.home-eyebrow {
    display: flex; align-items: center; gap: 9px; width: fit-content; margin-bottom: 22px;
    color: #8edcff; font-size: 11px; font-weight: 850; letter-spacing: .13em; text-transform: uppercase;
}
.home-eyebrow span { width: 7px; height: 7px; border-radius: 99px; background: var(--pl-cyan); box-shadow: 0 0 14px var(--pl-cyan); }
.home-hero h1 {
    max-width: 760px; margin: 0; color: #f8fbff; font-size: clamp(42px, 5vw, 70px);
    line-height: 1.03; font-weight: 900; letter-spacing: -.052em; text-wrap: balance;
    text-shadow: 0 5px 30px rgba(0, 0, 0, .52);
}
.home-hero h1 em { color: #35bdf7; font-style: normal; }
.home-hero-content > p {
    max-width: 630px; margin: 24px 0 0; color: #d1deec; font-size: clamp(15px, 1.45vw, 18px);
    line-height: 1.72; font-weight: 470; text-shadow: 0 3px 16px rgba(0, 0, 0, .68);
}
.home-hero-meta { display: flex; flex-wrap: wrap; gap: 10px; margin-top: 28px; }
.home-hero-meta > span {
    padding: 8px 13px; border-radius: 999px; color: #d7e6f5; font-size: 11px; font-weight: 750;
    letter-spacing: .06em; text-transform: uppercase; background: rgba(4, 13, 30, .58);
    border: 1px solid rgba(125, 211, 252, .20); backdrop-filter: blur(12px);
}
.home-provider i { display: inline-block; width: 6px; height: 6px; margin: 0 6px 1px 0; border-radius: 50%; background: var(--pl-emerald); box-shadow: 0 0 8px var(--pl-emerald); }
.home-hero-caption {
    position: absolute; right: 22px; bottom: 16px; color: rgba(226, 232, 240, .66);
    font-size: 10px; letter-spacing: .08em; text-transform: uppercase; text-shadow: 0 2px 8px #000;
}

.home-announcement {
    display: flex; gap: 12px; align-items: flex-start; margin: 22px 0 -4px; padding: 15px 17px;
    border: 1px solid rgba(251, 191, 36, .24); border-radius: var(--pl-radius-md);
    background: linear-gradient(135deg, rgba(120, 53, 15, .25), rgba(11, 19, 36, .82));
}
.home-announcement-mark { display: grid; place-items: center; width: 24px; height: 24px; border-radius: 8px; color: #1f1501; background: #fbbf24; font-weight: 900; }
.home-announcement strong { color: #fde68a; font-size: 13px; }
.home-announcement p { margin: 4px 0 0; color: #cbd5e1; font-size: 13px; }

.home-metric-grid { display: grid; grid-template-columns: repeat(4, minmax(0, 1fr)); gap: 16px; margin: 30px 0 58px; }
.home-metric {
    min-height: 142px; display: flex; flex-direction: column; justify-content: center; align-items: center;
    border: 1px solid var(--pl-border); border-radius: 20px;
    background: linear-gradient(155deg, rgba(14, 27, 51, .92), rgba(5, 12, 26, .96));
    box-shadow: inset 0 1px rgba(255, 255, 255, .04), 0 16px 42px rgba(0, 0, 0, .20);
}
.home-metric strong { color: var(--card-tone); font-size: clamp(34px, 4vw, 48px); line-height: 1; letter-spacing: -.04em; text-shadow: 0 0 26px color-mix(in srgb, var(--card-tone) 36%, transparent); }
.home-metric span { margin-top: 12px; color: #b1c4db; font-size: 11px; font-weight: 850; letter-spacing: .10em; text-transform: uppercase; }
.tone-cyan { --card-tone: var(--pl-cyan); }.tone-indigo { --card-tone: var(--pl-indigo); }
.tone-emerald { --card-tone: var(--pl-emerald); }.tone-amber { --card-tone: var(--pl-amber); }
.tone-rose { --card-tone: var(--pl-rose); }.tone-violet { --card-tone: var(--pl-violet); }

.home-section-head { max-width: 760px; margin: 0 0 22px; }
.home-section-head > span { color: var(--pl-cyan); font-size: 10px; font-weight: 850; letter-spacing: .15em; text-transform: uppercase; }
.home-section-head h2 { margin: 8px 0 0; color: #f7fbff; font-size: clamp(26px, 3vw, 36px); line-height: 1.15; letter-spacing: -.035em; }
.home-section-head p { margin: 9px 0 0; max-width: 650px; color: var(--pl-muted); font-size: 14px; line-height: 1.65; }

.home-feature-grid { display: grid; grid-template-columns: repeat(3, minmax(0, 1fr)); gap: 16px; margin-bottom: 58px; }
.home-feature {
    position: relative; overflow: hidden; min-height: 218px; padding: 24px;
    border: 1px solid var(--pl-border); border-radius: 20px;
    background: linear-gradient(155deg, rgba(12, 25, 48, .90), rgba(5, 12, 26, .96));
    box-shadow: inset 0 1px rgba(255, 255, 255, .04), 0 16px 40px rgba(0, 0, 0, .18);
    transition: transform .18s ease, border-color .18s ease, box-shadow .18s ease;
}
.home-feature::after { content: ""; position: absolute; width: 130px; height: 130px; right: -58px; top: -58px; border-radius: 50%; background: var(--card-tone); opacity: .09; filter: blur(18px); }
.home-feature:hover { transform: translateY(-3px); border-color: color-mix(in srgb, var(--card-tone) 38%, transparent); box-shadow: 0 20px 48px rgba(0, 0, 0, .26); }
.home-feature-index { display: grid; place-items: center; width: 38px; height: 38px; border-radius: 12px; color: #03101d; background: var(--card-tone); font-size: 11px; font-weight: 900; }
.home-feature h3 { margin: 22px 0 8px; color: #eef6ff; font-size: 17px; letter-spacing: -.015em; }
.home-feature p { margin: 0; color: #9aacc2; font-size: 13px; line-height: 1.68; }

.home-process {
    display: grid; grid-template-columns: repeat(4, minmax(0, 1fr)); overflow: hidden;
    margin-bottom: 58px; padding: 8px; border: 1px solid rgba(125, 211, 252, .13);
    border-radius: 22px; background: linear-gradient(135deg, rgba(14, 165, 233, .06), rgba(99, 102, 241, .045));
}
.home-process-step { position: relative; min-height: 176px; padding: 22px; border-right: 1px solid rgba(148, 163, 184, .10); }
.home-process-step:last-child { border-right: 0; }
.home-process-step > span { color: var(--card-tone); font-size: 10px; font-weight: 850; letter-spacing: .13em; text-transform: uppercase; }
.home-process-step h3 { margin: 10px 0 7px; color: #edf6ff; font-size: 16px; }
.home-process-step p { margin: 0; color: #93a5bc; font-size: 12.5px; line-height: 1.64; }
.st-key-home_quick_actions { margin: -4px 0 52px; padding: 18px; border: 1px solid var(--pl-border); border-radius: 20px; background: rgba(7, 15, 30, .58); }
.st-key-home_quick_actions .stButton > button { min-height: 48px !important; }

.home-footer { display: flex; justify-content: space-between; gap: 18px; flex-wrap: wrap; padding: 20px 0 4px; border-top: 1px solid rgba(148, 163, 184, .10); color: #a7bad2; font-size: 12px; letter-spacing: .025em; }
.home-footer strong { color: #8edcff; }

/* Dashboard polish remains generic so feature modules stay independent. */
.pl-card { min-height: 122px; border-color: var(--pl-border); background: linear-gradient(155deg, rgba(14, 27, 51, .88), rgba(7, 15, 30, .94)); box-shadow: 0 16px 38px rgba(0, 0, 0, .18); }
.pl-card .lbl { color: #b1c4db; }.pl-card .sub { color: #a7bad2; line-height: 1.55; }
.page-intro { border-color: rgba(125, 211, 252, .16); box-shadow: 0 22px 58px rgba(0, 0, 0, .22); }

@media (max-width: 1100px) {
    .home-hero { min-height: 470px; background-position: 58% 43%; }
    .home-hero-content { width: 72%; padding-left: 3.25rem; }
    .home-feature-grid { grid-template-columns: repeat(2, minmax(0, 1fr)); }
    .home-process { grid-template-columns: repeat(2, minmax(0, 1fr)); }
    .home-process-step:nth-child(2) { border-right: 0; }
    .home-process-step:nth-child(-n+2) { border-bottom: 1px solid rgba(148, 163, 184, .10); }
}
@media (max-width: 760px) {
    .block-container { padding: 1rem 1rem 2.5rem !important; }
    .home-hero { min-height: 540px; margin: -1rem -1rem 0; align-items: flex-end; background-position: 66% center; }
    .home-hero::before { background: linear-gradient(0deg, rgba(1, 7, 20, .98) 0%, rgba(2, 9, 24, .85) 48%, rgba(2, 8, 20, .18) 100%); }
    .home-hero-content { width: 100%; padding: 44px 22px 38px; }
    .home-hero h1 { font-size: clamp(36px, 11vw, 50px); }
    .home-hero-content > p { font-size: 15px; line-height: 1.62; }
    .home-hero-caption { display: none; }
    .home-metric-grid { grid-template-columns: repeat(2, minmax(0, 1fr)); gap: 11px; margin: 20px 0 44px; }
    .home-metric { min-height: 116px; }.home-metric strong { font-size: 34px; }
    .home-feature-grid, .home-process { grid-template-columns: 1fr; }
    .home-feature { min-height: 190px; }
    .home-process-step { min-height: 0; border-right: 0; border-bottom: 1px solid rgba(148, 163, 184, .10); }
    .home-process-step:last-child { border-bottom: 0; }
    .home-section-head { margin-bottom: 17px; }
}
@media (max-width: 420px) {
    .home-hero-meta { align-items: flex-start; flex-direction: column; }
    .home-metric-grid { grid-template-columns: 1fr 1fr; }
    .home-metric span { font-size: 10.5px; letter-spacing: .06em; text-align: center; }
}
@media (prefers-reduced-motion: reduce) {
    *, *::before, *::after { scroll-behavior: auto !important; animation-duration: .01ms !important; animation-iteration-count: 1 !important; transition-duration: .01ms !important; }
}
</style>
"""


def inject_theme() -> None:
    """Inject the global stylesheet (call once per script run)."""
    st.markdown(CSS, unsafe_allow_html=True)
    st.markdown(DASHBOARD_CSS, unsafe_allow_html=True)
    st.markdown(UI_REFINEMENT_CSS, unsafe_allow_html=True)

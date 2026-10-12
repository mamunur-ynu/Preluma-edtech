"""
components/charts.py — Plotly figures for the dashboards.

Pure functions: data in, ``plotly.graph_objects.Figure`` out.  No Streamlit calls here, so the
same figures can be reused by a future React/FastAPI front end (``fig.to_json()``).
"""

from __future__ import annotations

from typing import Sequence

import plotly.graph_objects as go

from components.theme import PALETTE

_LAYOUT = dict(
    template="plotly_dark",
    paper_bgcolor="rgba(0,0,0,0)",
    plot_bgcolor="rgba(0,0,0,0)",
    font=dict(color=PALETTE["text"], size=12),
    margin=dict(l=10, r=10, t=40, b=10),
)


def _base(fig: go.Figure, title: str, height: int = 300) -> go.Figure:
    fig.update_layout(title=dict(text=title, font=dict(size=14)), height=height, **_LAYOUT)
    return fig


def _mastery_color(value: float) -> str:
    return PALETTE["good"] if value >= 75 else PALETTE["warn"] if value >= 60 else PALETTE["bad"]


def mastery_bar(topics: Sequence[tuple[str, float]], title: str = "Topic mastery") -> go.Figure:
    """Horizontal bars, one per topic, coloured by strength."""
    names = [t for t, _ in topics]
    values = [v for _, v in topics]
    fig = go.Figure(go.Bar(x=values, y=names, orientation="h", marker_color=[_mastery_color(v) for v in values],
                           text=[f"{v:.0f}%" for v in values], textposition="outside"))
    fig.update_xaxes(range=[0, 118], gridcolor="rgba(148,163,184,.12)", tickvals=[0, 25, 50, 75, 100])
    fig.update_yaxes(autorange="reversed")
    return _base(fig, title, height=max(240, 34 * len(names) + 80))


def skill_radar(scores: dict[str, float], title: str = "Skill profile") -> go.Figure:
    """Radar chart of question-skill mastery (recall, understanding, application …)."""
    labels = list(scores) or ["–"]
    values = [scores[k] for k in scores] or [0]
    fig = go.Figure(go.Scatterpolar(r=values + values[:1], theta=labels + labels[:1], fill="toself",
                                    line_color=PALETTE["primary"], fillcolor="rgba(56,189,248,.25)"))
    fig.update_polars(radialaxis=dict(range=[0, 100], gridcolor="rgba(148,163,184,.2)"), bgcolor="rgba(0,0,0,0)")
    return _base(fig, title, height=320)


def score_trend(points: Sequence[tuple[str, str, float]], title: str = "Recent quiz scores") -> go.Figure:
    """Line chart of the latest attempts (oldest → newest)."""
    fig = go.Figure(go.Scatter(x=[f"{d}" for d, _, _ in points], y=[p for _, _, p in points],
                               mode="lines+markers", line=dict(color=PALETTE["accent"], width=3),
                               marker=dict(size=9), text=[t for _, t, _ in points],
                               hovertemplate="%{text}<br>%{y:.0f}%<extra></extra>"))
    fig.update_yaxes(range=[0, 105], gridcolor="rgba(148,163,184,.12)")
    return _base(fig, title, height=280)


def distribution_bar(distribution: Sequence[dict], title: str = "Readiness distribution") -> go.Figure:
    fig = go.Figure(go.Bar(x=[d["band"] for d in distribution], y=[d["count"] for d in distribution],
                           marker_color=[PALETTE["bad"], PALETTE["warn"], PALETTE["primary"], PALETTE["good"],
                                         PALETTE["good"]][: len(distribution)] or PALETTE["primary"]))
    fig.update_yaxes(gridcolor="rgba(148,163,184,.12)", dtick=1)
    return _base(fig, title, height=280)


def topic_difficulty(ranking: Sequence[dict], title: str = "Hardest topics (class average mastery)") -> go.Figure:
    rows = list(ranking)[:10]
    values = [r["average_mastery"] for r in rows]
    fig = go.Figure(go.Bar(x=values, y=[r.get("title", r["topic"]) for r in rows], orientation="h",
                           marker_color=[_mastery_color(v) for v in values],
                           text=[f"{v:.0f}%  ({r['students_at_risk']} at risk)" for v, r in zip(values, rows)],
                           textposition="outside"))
    fig.update_xaxes(range=[0, 120], gridcolor="rgba(148,163,184,.12)")
    fig.update_yaxes(autorange="reversed")
    return _base(fig, title, height=max(260, 36 * len(rows) + 80))


def daily_trend(daily: Sequence[dict], title: str = "Class average score per day") -> go.Figure:
    fig = go.Figure()
    fig.add_bar(x=[d["day"] for d in daily], y=[d["attempts"] for d in daily], name="Attempts",
                marker_color="rgba(129,140,248,.35)", yaxis="y2")
    fig.add_scatter(x=[d["day"] for d in daily], y=[d["average"] for d in daily], name="Average %",
                    mode="lines+markers", line=dict(color=PALETTE["primary"], width=3))
    fig.update_layout(yaxis=dict(range=[0, 105], gridcolor="rgba(148,163,184,.12)"),
                      yaxis2=dict(overlaying="y", side="right", showgrid=False), legend=dict(orientation="h"))
    return _base(fig, title, height=300)


def mistakes_bar(mistakes: Sequence[dict], title: str = "Most common mistakes") -> go.Figure:
    labels = [f"{m['topic']} · {m['concept']}" for m in mistakes]
    fig = go.Figure(go.Bar(x=[m["count"] for m in mistakes], y=labels, orientation="h", marker_color=PALETTE["bad"]))
    fig.update_yaxes(autorange="reversed")
    return _base(fig, title, height=max(240, 34 * len(labels) + 80))


def completion_gauge(percent: float, title: str = "Course completion") -> go.Figure:
    fig = go.Figure(go.Indicator(mode="gauge+number", value=percent, number={"suffix": "%"},
                                 gauge=dict(axis=dict(range=[0, 100]), bar=dict(color=PALETTE["primary"]))))
    return _base(fig, title, height=240)

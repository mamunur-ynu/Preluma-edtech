"""Service layer: use-case orchestration between the UI, the pure core, the database and the AI layer.

Rules: services never import Streamlit; they accept and return plain values / dataclasses
(never ORM objects); each public function is one use case a REST endpoint could expose.
"""

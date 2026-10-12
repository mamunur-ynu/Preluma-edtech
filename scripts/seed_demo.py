"""
Fill an empty database with a realistic demo class (for screenshots and live demos).

    PRELUMA_DEMO_PASSWORD='Demo-Passw0rd!' python scripts/seed_demo.py

Creates one teacher (``demo_teacher``), six students (``demo_student`` + five classmates), enrols them
in the default courses and replays a few weeks of quiz attempts so every chart has data.
The password comes from the environment (or is generated and printed once) — nothing is hard-coded.
"""

from __future__ import annotations

import os
import random
import secrets
import sys
from datetime import timedelta
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from auth import ValidationError, create_user, username_exists  # noqa: E402
from database.connection import init_db  # noqa: E402
from services import course_service, learning_service  # noqa: E402
from services._common import now_utc  # noqa: E402
from services.user_service import get_user  # noqa: E402

CLASSMATES = [("demo_student", "Alice Wang"), ("li_ming", "Li Ming"), ("zhang_wei", "Zhang Wei"),
              ("chen_yu", "Chen Yu"), ("wang_fang", "Wang Fang"), ("liu_yang", "Liu Yang")]
TOPICS = ["python programming", "algorithms and complexity", "data structures", "statistics", "machine learning",
          "neural network", "database management system"]
# How strong each student is (probability of answering correctly); Alice is strong at Python, weak at algorithms.
ABILITY = {"demo_student": 0.78, "li_ming": 0.9, "zhang_wei": 0.6, "chen_yu": 0.7, "wang_fang": 0.5, "liu_yang": 0.82}


def main() -> None:
    password = os.environ.get("PRELUMA_DEMO_PASSWORD") or secrets.token_urlsafe(12)
    init_db()
    course_service.ensure_default_catalog()
    rng = random.Random(42)
    try:
        if not username_exists("demo_teacher"):
            create_user("demo_teacher", password, "Prof. Li Hua", "teacher")
        for username, name in CLASSMATES:
            if not username_exists(username):
                create_user(username, password, name)
    except ValidationError as exc:
        raise SystemExit(f"Password rejected: {exc}")

    courses = course_service.list_courses()
    now = now_utc()
    for username, _ in CLASSMATES:
        user = get_user(username)
        for course in courses[:2]:
            course_service.enroll(user.id, course.id)
        ability = ABILITY[username]
        for day in range(21, -1, -1):
            if rng.random() < 0.55 and not (username == "demo_student" and day < 4):
                continue
            topic = rng.choice(TOPICS[:4] if day > 10 else TOPICS)
            p = ability - (0.35 if username == "demo_student" and topic == "algorithms and complexity" else 0)
            p += min(0.15, (21 - day) * 0.007)                                  # students improve over time
            score = sum(rng.random() < max(0.05, min(0.98, p)) for _ in range(5))
            learning_service.record_quiz_attempt(user.id, topic, score, 5, duration_seconds=rng.randint(60, 240),
                                                 learning_mode=rng.choice(["Fast Review", "Deep Understanding"]),
                                                 when=now - timedelta(days=day, hours=rng.randint(0, 6)))
    print("Demo class created.")
    print("Teacher: demo_teacher   Students: " + ", ".join(u for u, _ in CLASSMATES))
    if not os.environ.get("PRELUMA_DEMO_PASSWORD"):
        print(f"Generated password (shown once): {password}")


if __name__ == "__main__":
    main()

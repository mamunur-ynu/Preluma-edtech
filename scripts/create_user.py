"""
Create (or promote) an account from the command line — handy for the first admin/teacher.

    python scripts/create_user.py alice "Alice Wang" --role teacher
    PRELUMA_PASSWORD='S3cure-pass!' python scripts/create_user.py alice "Alice Wang"   # non-interactive

The password is read from a hidden prompt (or ``PRELUMA_PASSWORD``), never from argv, so it does
not end up in shell history or the process list.
"""

from __future__ import annotations

import argparse
import getpass
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from auth import ValidationError, create_user  # noqa: E402
from database.connection import init_db  # noqa: E402


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("username")
    parser.add_argument("full_name")
    parser.add_argument("--role", choices=["student", "teacher", "admin"], default="student")
    args = parser.parse_args()

    password = os.environ.get("PRELUMA_PASSWORD") or getpass.getpass("Password (min 8 chars): ")
    init_db()
    try:
        user = create_user(args.username, password, args.full_name, args.role)
    except ValidationError as exc:
        print(f"Could not create the account: {exc}", file=sys.stderr)
        return 1
    print(f"Created {user.role} account '{user.username}' (id {user.id}).")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

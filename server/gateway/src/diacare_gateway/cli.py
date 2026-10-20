"""Command-line tools for the gateway.

Create an account while registration is closed (for example a demo patient):

    uv run python -m diacare_gateway.cli create-user --email demo@example.test --demo
"""

import argparse
import getpass
import sys

from diacare_gateway.auth.users import create_user
from diacare_gateway.config import get_settings
from diacare_gateway.db.models import ROLES
from diacare_shared.db import make_engine, make_session_factory
from diacare_shared.errors import AppError

MIN_PASSWORD_LENGTH = 10


def _read_password(from_stdin: bool) -> str:
    if from_stdin:
        return sys.stdin.readline().rstrip("\r\n")
    first = getpass.getpass("Password: ")
    if getpass.getpass("Repeat password: ") != first:
        raise SystemExit("The two passwords differ.")
    return first


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="diacare_gateway.cli")
    commands = parser.add_subparsers(dest="command", required=True)
    create = commands.add_parser("create-user", help="Create an account.")
    create.add_argument("--email", required=True)
    create.add_argument("--display-name")
    create.add_argument("--role", choices=ROLES, default="patient")
    create.add_argument("--demo", action="store_true", help="Mark it as a demo/test account.")
    create.add_argument(
        "--password-stdin", action="store_true", help="Read the password from one line of stdin."
    )
    args = parser.parse_args(argv)

    url = get_settings().gateway_database_url
    if not url:
        print("GATEWAY_DATABASE_URL is not set.", file=sys.stderr)
        return 2
    password = _read_password(args.password_stdin)
    if len(password) < MIN_PASSWORD_LENGTH:
        print(f"The password needs at least {MIN_PASSWORD_LENGTH} characters.", file=sys.stderr)
        return 2

    engine = make_engine(url, "core")
    try:
        with make_session_factory(engine)() as session:
            user = create_user(
                session,
                email=args.email,
                password=password,
                display_name=args.display_name,
                role=args.role,
                is_demo=args.demo,
            )
            session.commit()
            print(f"Created {user.role} account {user.id} ({user.email})")
    except AppError as exc:
        print(exc.message, file=sys.stderr)
        return 1
    finally:
        engine.dispose()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

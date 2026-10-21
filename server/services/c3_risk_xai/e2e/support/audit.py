"""Read or remove the audit rows of the browser-check devices (never prints the database URL).

    python audit.py show <device_id>        -> JSON list of {action, detail, columns}
    python audit.py purge <id> [<id> ...]   -> deletes leftover rows of these test devices

Only device IDs starting with "e2e0" are accepted, so real devices can never be touched.
"""

import json
import sys

from sqlalchemy import text

from c3_risk_xai.db.repository import make_engine
from c3_risk_xai.settings import get_settings

PREFIX = "e2e0"


def main() -> None:
    command, ids = sys.argv[1], sys.argv[2:]
    if not ids or any(not i.startswith(PREFIX) for i in ids):
        sys.exit(f"only test device IDs starting with {PREFIX!r} are allowed")
    engine = make_engine(get_settings().database_url)
    with engine.begin() as conn:
        if command == "show":
            result = conn.execute(
                text("SELECT * FROM c3.audit_log WHERE device_id = :d ORDER BY created_at"),
                {"d": ids[0]},
            )
            columns = list(result.keys())
            rows = [{"action": r.action, "detail": r.detail} for r in result]
            print(json.dumps({"columns": columns, "rows": rows}))
        elif command == "purge":
            removed = {}
            for table in ("risk_profiles", "audit_log"):
                result = conn.execute(
                    text(f"DELETE FROM c3.{table} WHERE device_id = ANY(:ids)"), {"ids": ids}
                )
                removed[table] = result.rowcount
            print(json.dumps(removed))
        else:
            sys.exit(f"unknown command {command!r}")


if __name__ == "__main__":
    main()

import json
import sys
from decimal import Decimal
from pathlib import Path
from typing import Any

import psycopg

from agent_platform.config import get_settings

GOLDEN = Path(sys.argv[1]) if len(sys.argv) > 1 else Path("evals/tasks/golden_v2.jsonl")


def normalise(value: Any) -> Any:
    """Decimals -> float rounded to 2 dp, sp answers are plain json."""
    if isinstance(value, Decimal):
        value = float(value)
    if isinstance(value, float):
        return round(value, 2)
    return value


def main() -> int:
    lines = GOLDEN.read_text(encoding="utf-8").splitlines()
    tasks = [json.loads(line) for line in lines if line.strip()]

    ids = [t["id"] for t in tasks]
    if len(ids) != len(set(ids)):
        print("[FAIL] duplicate tasks ids")
        return 1

    with psycopg.connect(get_settings().database_url) as conn:
        conn.read_only = True
        for t in tasks:
            sql = t.get("ground_truth_sql")
            if not sql:
                t["expected"] = None
                print(f"{t['id']}  {t['category']:<13} -> (no SQL: {t['expected_behavior']})")
                continue
            rows = conn.execute(sql).fetchall()
            if t["answer_type"] == "list":
                t["expected"] = [normalise(r[0]) for r in rows]
            else:
                if len(rows) != 1:
                    print(f"[FAIL] {t['id']}: expected 1 row, got {len(rows)}")
                    return 1
                t["expected"] = normalise(rows[0][0])
            print(f"{t['id']}  {t['category']:<13} -> {t['expected']}")
    GOLDEN.write_text(
        "".join(json.dumps(t, ensure_ascii=False) + "\n" for t in tasks),
        encoding="utf-8",
        newline="\n",
    )


if __name__ == "__main__":
    sys.exit(main())

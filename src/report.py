#!/usr/bin/env python3
"""Разбор журнала ИИ-агента Лавки (вариант D)."""
import json
from collections import Counter

LOG = "datasets/D/logs/agent.jsonl"
INCIDENT_TIME = "2026-09-16T13:17:00"  
BENEFICIARY_HINT = "student_03"


def load(path):
    rows = []
    with open(path, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                rows.append(json.loads(line))
    return rows


def main():
    rows = load(LOG)

    owner = {}
    for r in rows:
        if r.get("tool") == "create_order" and r.get("result", {}).get("ok"):
            oid = r["result"]["data"]["order_id"]
            owner[oid] = r["args"]["user_id"]

    start = None
    for r in rows:
        if r["time"] > INCIDENT_TIME and r.get("tool") == "cancel_order" \
                and r.get("result", {}).get("ok"):
            start = r["time"]
            break

    after = [r for r in rows if r["time"] >= start]

    created_by = Counter(
        r["args"]["user_id"] for r in after
        if r.get("tool") == "create_order" and r.get("result", {}).get("ok")
    )
    beneficiary = created_by.most_common(1)[0][0] if created_by else BENEFICIARY_HINT

    cancelled = set()
    for r in after:
        if r.get("tool") == "cancel_order" and r.get("result", {}).get("ok"):
            oid = r["args"]["order_id"]
            if owner.get(oid) and owner[oid] != beneficiary:
                cancelled.add(oid)

    made_for = {
        r["result"]["data"]["order_id"] for r in after
        if r.get("tool") == "create_order" and r.get("result", {}).get("ok")
        and r["args"]["user_id"] == beneficiary
    }

    print(f"первый подозрительный вызов: {start}")
    print(f"отменено чужих заказов: {len(cancelled)}")
    print(f"аккаунт выгодоприобретателя: {beneficiary}")
    print(f"оформлено на этот аккаунт: {len(made_for)}")


if __name__ == "__main__":
    main()
#!/usr/bin/env python3
"""Build a deterministic AE/TE data-permission sync plan without external writes."""

from __future__ import annotations

import argparse
import csv
import hashlib
import io
import json
import sys
from collections import defaultdict
from pathlib import Path
from typing import Any


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--sheet-csv", required=True, help="Normalized or raw source CSV.")
    parser.add_argument("--state-json", required=True, help="Normalized current AE/TE state JSON.")
    parser.add_argument("--output", required=True, help="Output plan JSON path.")
    parser.add_argument("--account-col", default="account")
    parser.add_argument("--platform-col", default="platform")
    parser.add_argument("--permission-col", default="data_permission")
    parser.add_argument("--sync-mode", choices=("additive", "exact"), default="additive")
    parser.add_argument(
        "--new-member-role",
        action="append",
        default=[],
        help="Explicit role for new members. Repeat for multiple roles.",
    )
    parser.add_argument(
        "--allow-unknown-platform",
        action="store_true",
        help="Include exact unknown platform values after explicit user approval.",
    )
    return parser.parse_args()


def fail(message: str) -> None:
    raise ValueError(message)


def require_list(value: Any, field: str) -> list[Any]:
    if not isinstance(value, list):
        fail(f"{field} must be an array")
    return value


def is_positive_int(value: Any) -> bool:
    return isinstance(value, int) and not isinstance(value, bool) and value > 0


def canonical_json(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def normalize_sheet(
    path: Path, account_col: str, platform_col: str, permission_col: str
) -> tuple[list[dict[str, Any]], list[dict[str, Any]], str, int]:
    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        reader = csv.DictReader(handle)
        if reader.fieldnames is None:
            fail("source CSV has no header")
        required = {account_col, platform_col, permission_col}
        missing = sorted(required - set(reader.fieldnames))
        if missing:
            fail(f"source CSV is missing columns: {', '.join(missing)}")

        raw_rows: list[dict[str, Any]] = []
        for row_number, row in enumerate(reader, start=2):
            account = (row.get(account_col) or "").strip()
            platform = (row.get(platform_col) or "").strip()
            permission = (row.get(permission_col) or "").strip()
            if not account and not platform and not permission:
                continue
            raw_rows.append(
                {
                    "account": account,
                    "platform": platform,
                    "data_permission": permission,
                    "source_rows": [row_number],
                }
            )

    problems: list[dict[str, Any]] = []
    unique: dict[tuple[str, str, str], dict[str, Any]] = {}
    for row in raw_rows:
        blank_fields = [
            field
            for field in ("account", "platform", "data_permission")
            if not row[field]
        ]
        if blank_fields:
            problems.append(
                {
                    "code": "BLANK_REQUIRED_FIELD",
                    "source_rows": row["source_rows"],
                    "fields": blank_fields,
                }
            )
            continue
        key = (row["account"], row["platform"], row["data_permission"])
        if key in unique:
            unique[key]["source_rows"].extend(row["source_rows"])
        else:
            unique[key] = row

    normalized = sorted(
        unique.values(), key=lambda row: (row["account"], row["data_permission"], row["platform"])
    )

    case_variants: dict[str, set[str]] = defaultdict(set)
    permission_platforms: dict[str, set[str]] = defaultdict(set)
    account_permission_platforms: dict[tuple[str, str], set[str]] = defaultdict(set)
    for row in normalized:
        case_variants[row["account"].casefold()].add(row["account"])
        permission_platforms[row["data_permission"]].add(row["platform"])
        account_permission_platforms[(row["account"], row["data_permission"])].add(
            row["platform"]
        )

    for variants in case_variants.values():
        if len(variants) > 1:
            problems.append(
                {"code": "AMBIGUOUS_ACCOUNT_CASE", "accounts": sorted(variants)}
            )
    for permission, platforms in sorted(permission_platforms.items()):
        if len(platforms) > 1:
            problems.append(
                {
                    "code": "PERMISSION_PLATFORM_CONFLICT",
                    "data_permission": permission,
                    "platforms": sorted(platforms),
                }
            )
    for (account, permission), platforms in sorted(account_permission_platforms.items()):
        if len(platforms) > 1:
            problems.append(
                {
                    "code": "ACCOUNT_PERMISSION_CONFLICT",
                    "account": account,
                    "data_permission": permission,
                    "platforms": sorted(platforms),
                }
            )

    buffer = io.StringIO(newline="")
    writer = csv.DictWriter(
        buffer, fieldnames=["account", "platform", "data_permission"], lineterminator="\n"
    )
    writer.writeheader()
    for row in normalized:
        writer.writerow({key: row[key] for key in writer.fieldnames})
    snapshot_bytes = buffer.getvalue().encode("utf-8")
    snapshot_hash = hashlib.sha256(snapshot_bytes).hexdigest()
    duplicate_rows = sum(max(0, len(row["source_rows"]) - 1) for row in normalized)
    return normalized, problems, snapshot_hash, duplicate_rows


def index_by_account(items: list[dict[str, Any]], field: str) -> tuple[dict[str, dict[str, Any]], list[dict[str, Any]]]:
    indexed: dict[str, dict[str, Any]] = {}
    problems: list[dict[str, Any]] = []
    for item in items:
        if not isinstance(item, dict):
            fail(f"{field} entries must be objects")
        account = str(item.get("account") or "").strip()
        if not account:
            fail(f"{field} entry is missing account")
        key = account.casefold()
        if key in indexed:
            problems.append(
                {"code": "AMBIGUOUS_STATE_ACCOUNT", "account": account, "section": field}
            )
        else:
            indexed[key] = item
    return indexed, problems


def build_plan(args: argparse.Namespace) -> dict[str, Any]:
    sheet_path = Path(args.sheet_csv)
    state_path = Path(args.state_json)
    if not sheet_path.is_file():
        fail(f"sheet CSV not found: {sheet_path}")
    if not state_path.is_file():
        fail(f"state JSON not found: {state_path}")

    rows, blockers, source_hash, duplicate_rows = normalize_sheet(
        sheet_path, args.account_col, args.platform_col, args.permission_col
    )
    state = json.loads(state_path.read_text(encoding="utf-8"))
    if not isinstance(state, dict):
        fail("state JSON must be an object")
    project_id = state.get("project_id")
    if not is_positive_int(project_id):
        fail("state project_id must be a positive integer")
    host = str(state.get("host") or "").strip()
    if not host:
        fail("state host is required")

    platform_candidates = require_list(state.get("platform_candidates"), "platform_candidates")
    candidate_values = {str(value) for value in platform_candidates}
    if not candidate_values:
        blockers.append({"code": "PLATFORM_CANDIDATES_UNAVAILABLE"})

    data_powers = require_list(state.get("data_powers"), "data_powers")
    members = require_list(state.get("members"), "members")
    candidates = require_list(state.get("candidates"), "candidates")

    powers_by_name: dict[str, dict[str, Any]] = {}
    powers_by_id: dict[int, dict[str, Any]] = {}
    for power in data_powers:
        if not isinstance(power, dict):
            fail("data_powers entries must be objects")
        name = str(power.get("name") or "").strip()
        power_id = power.get("id")
        if not name or not is_positive_int(power_id):
            fail("every data power requires integer id and non-empty name")
        if name in powers_by_name:
            blockers.append({"code": "DUPLICATE_DATA_PERMISSION_NAME", "name": name})
        powers_by_name[name] = power
        powers_by_id[power_id] = power

    members_by_account, member_problems = index_by_account(members, "members")
    candidates_by_account, candidate_problems = index_by_account(candidates, "candidates")
    blockers.extend(member_problems)
    blockers.extend(candidate_problems)

    source_accounts = {row["account"].casefold() for row in rows}
    permission_platform = {
        row["data_permission"]: row["platform"] for row in rows
    }
    unknown_platforms = sorted(
        {row["platform"] for row in rows if row["platform"] not in candidate_values}
    )
    risk_flags: list[dict[str, Any]] = []
    if unknown_platforms:
        if args.allow_unknown_platform:
            risk_flags.append(
                {
                    "code": "UNKNOWN_PLATFORM_OVERRIDE",
                    "platforms": unknown_platforms,
                }
            )
        else:
            blockers.append(
                {"code": "BLOCKED_UNKNOWN_PLATFORM", "platforms": unknown_platforms}
            )

    data_power_actions: list[dict[str, Any]] = []
    for permission, platform in sorted(permission_platform.items()):
        current = powers_by_name.get(permission)
        if current is None:
            data_power_actions.append(
                {
                    "action": "CREATE_DATA_PERMISSION",
                    "name": permission,
                    "target_platform": platform,
                    "target_filter": {"property": "platform", "operator": "eq", "values": [platform]},
                }
            )
            continue
        current_platform = current.get("platform")
        if current_platform is None:
            blockers.append(
                {
                    "code": "AMBIGUOUS_EXISTING_FILTER",
                    "data_power_id": current["id"],
                    "name": permission,
                    "filter_summary": current.get("filter_summary"),
                }
            )
            continue
        if current_platform == platform:
            continue

        if "out_of_scope_member_count" in current:
            out_of_scope_count = current.get("out_of_scope_member_count")
            if not isinstance(out_of_scope_count, int) or out_of_scope_count < 0:
                fail("out_of_scope_member_count must be a non-negative integer")
        elif isinstance(current.get("member_accounts"), list):
            out_of_scope_count = sum(
                1
                for account in current["member_accounts"]
                if str(account).casefold() not in source_accounts
            )
        else:
            blockers.append(
                {
                    "code": "SHARED_PERMISSION_IMPACT_UNKNOWN",
                    "data_power_id": current["id"],
                    "name": permission,
                }
            )
            continue
        data_power_actions.append(
            {
                "action": "UPDATE_DATA_PERMISSION",
                "id": current["id"],
                "name": permission,
                "current_platform": current_platform,
                "target_platform": platform,
                "access_direction": "CHANGED",
                "out_of_scope_member_count": out_of_scope_count,
                "target_filter": {"property": "platform", "operator": "eq", "values": [platform]},
            }
        )
        if out_of_scope_count:
            risk_flags.append(
                {
                    "code": "SHARED_PERMISSION_UPDATE",
                    "name": permission,
                    "out_of_scope_member_count": out_of_scope_count,
                }
            )

    required_by_account: dict[str, set[str]] = defaultdict(set)
    display_account: dict[str, str] = {}
    source_rows_by_account: dict[str, set[int]] = defaultdict(set)
    for row in rows:
        key = row["account"].casefold()
        required_by_account[key].add(row["data_permission"])
        display_account[key] = row["account"]
        source_rows_by_account[key].update(row["source_rows"])

    member_actions: list[dict[str, Any]] = []
    unchanged: list[dict[str, Any]] = []
    for key in sorted(required_by_account, key=lambda value: display_account[value]):
        account = display_account[key]
        required_names = sorted(required_by_account[key])
        member = members_by_account.get(key)
        if member is None:
            candidate = candidates_by_account.get(key)
            if candidate is None:
                blockers.append(
                    {"code": "ACCOUNT_NOT_RESOLVED", "account": account, "source_rows": sorted(source_rows_by_account[key])}
                )
                continue
            candidate_user_id = candidate.get("user_id")
            if not is_positive_int(candidate_user_id):
                blockers.append(
                    {
                        "code": "INVALID_CANDIDATE_USER_ID",
                        "account": account,
                        "source_rows": sorted(source_rows_by_account[key]),
                    }
                )
                continue
            if not args.new_member_role:
                blockers.append(
                    {"code": "NEW_MEMBER_ROLE_REQUIRED", "account": account, "source_rows": sorted(source_rows_by_account[key])}
                )
                continue
            member_actions.append(
                {
                    "action": "ADD_PROJECT_MEMBER",
                    "account": account,
                    "user_id": candidate_user_id,
                    "target_role_names": sorted(set(args.new_member_role)),
                    "target_data_permission_names": required_names,
                    "permission_additions": required_names,
                    "permission_removals": [],
                    "source_rows": sorted(source_rows_by_account[key]),
                }
            )
            continue

        member_user_id = member.get("user_id")
        if not is_positive_int(member_user_id):
            blockers.append(
                {
                    "code": "INVALID_MEMBER_USER_ID",
                    "account": account,
                    "source_rows": sorted(source_rows_by_account[key]),
                }
            )
            continue
        role_names = require_list(member.get("role_names"), f"member {account} role_names")
        if not role_names or any(
            not isinstance(role, str) or not role.strip() for role in role_names
        ):
            blockers.append(
                {
                    "code": "INVALID_MEMBER_ROLES",
                    "account": account,
                    "source_rows": sorted(source_rows_by_account[key]),
                }
            )
            continue
        power_ids = require_list(member.get("data_power_ids"), f"member {account} data_power_ids")
        current_names = sorted(
            powers_by_id[power_id]["name"] for power_id in power_ids if power_id in powers_by_id
        )
        unknown_ids = sorted(power_id for power_id in power_ids if power_id not in powers_by_id)
        if unknown_ids:
            blockers.append(
                {"code": "UNKNOWN_ASSIGNED_DATA_POWER", "account": account, "data_power_ids": unknown_ids}
            )
            continue
        current_set = set(current_names)
        required_set = set(required_names)
        if args.sync_mode == "additive":
            target_set = current_set | required_set
        else:
            target_set = required_set
        additions = sorted(target_set - current_set)
        removals = sorted(current_set - target_set)
        if not additions and not removals:
            unchanged.append(
                {
                    "account": account,
                    "role_names": list(role_names),
                    "data_permission_names": sorted(current_set),
                    "source_rows": sorted(source_rows_by_account[key]),
                }
            )
            continue
        member_actions.append(
            {
                "action": "UPDATE_PROJECT_MEMBER",
                "account": account,
                "user_id": member_user_id,
                "current_role_names": list(role_names),
                "target_role_names": list(role_names),
                "current_data_permission_names": sorted(current_set),
                "target_data_permission_names": sorted(target_set),
                "permission_additions": additions,
                "permission_removals": removals,
                "source_rows": sorted(source_rows_by_account[key]),
            }
        )

    if args.sync_mode == "additive":
        unexpected_removals = [
            action for action in member_actions if action.get("permission_removals")
        ]
        if unexpected_removals:
            fail("additive mode generated permission removals")

    action_count = len(data_power_actions) + len(member_actions)
    status = "BLOCKED" if blockers else ("READY_FOR_APPROVAL" if action_count else "NO_CHANGE")
    plan: dict[str, Any] = {
        "status": status,
        "scope": {
            "host": host,
            "project_id": project_id,
            "project_name": state.get("project_name"),
            "sync_mode": args.sync_mode,
        },
        "source": {
            "path": str(sheet_path),
            "normalized_rows": len(rows),
            "deduplicated_rows": duplicate_rows,
            "sha256": source_hash,
        },
        "summary": {
            "data_permission_actions": len(data_power_actions),
            "member_actions": len(member_actions),
            "unchanged_accounts": len(unchanged),
            "blockers": len(blockers),
            "risk_flags": len(risk_flags),
        },
        "blockers": blockers,
        "risk_flags": risk_flags,
        "data_permission_actions": data_power_actions,
        "member_actions": member_actions,
        "unchanged_accounts": unchanged,
    }
    plan["plan_sha256"] = hashlib.sha256(canonical_json(plan).encode("utf-8")).hexdigest()
    return plan


def main() -> int:
    args = parse_args()
    try:
        plan = build_plan(args)
        output = Path(args.output)
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_text(json.dumps(plan, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        print(json.dumps({"status": plan["status"], "output": str(output), "summary": plan["summary"]}, indent=2))
        return 2 if plan["status"] == "BLOCKED" else 0
    except (OSError, ValueError, json.JSONDecodeError) as exc:
        print(json.dumps({"status": "ERROR", "error": str(exc)}), file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())

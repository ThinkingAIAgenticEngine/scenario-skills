#!/usr/bin/env python3
"""Behavioral tests for the deterministic permission sync planner."""

from __future__ import annotations

import csv
import json
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace

from build_sync_plan import build_plan


class PlannerTest(unittest.TestCase):
    def setUp(self) -> None:
        self.temp = tempfile.TemporaryDirectory(prefix="ae-feishu-sync-test-")
        self.root = Path(self.temp.name)
        self.state = {
            "host": "https://example.invalid",
            "project_id": 1364,
            "project_name": "Test Project",
            "platform_candidates": ["iOS", "Android"],
            "data_powers": [
                {
                    "id": 10,
                    "name": "iOS Data",
                    "platform": "iOS",
                    "filter_summary": "platform = iOS",
                    "member_accounts": ["alice@example.com"],
                },
                {
                    "id": 11,
                    "name": "Android Data",
                    "platform": "Android",
                    "filter_summary": "platform = Android",
                    "member_accounts": ["bob@example.com"],
                },
                {
                    "id": 12,
                    "name": "Legacy Data",
                    "platform": "Android",
                    "filter_summary": "platform = Android",
                    "member_accounts": ["bob@example.com"],
                },
            ],
            "members": [
                {
                    "account": "alice@example.com",
                    "user_id": 501,
                    "role_names": ["analyst", "member"],
                    "data_power_ids": [10],
                },
                {
                    "account": "bob@example.com",
                    "user_id": 502,
                    "role_names": ["admin"],
                    "data_power_ids": [11, 12],
                },
            ],
            "candidates": [{"account": "carol@example.com", "user_id": 503}],
        }

    def tearDown(self) -> None:
        self.temp.cleanup()

    def plan(
        self,
        rows: list[dict[str, str]],
        *,
        state: dict | None = None,
        sync_mode: str = "additive",
        roles: list[str] | None = None,
        allow_unknown_platform: bool = False,
    ) -> dict:
        csv_path = self.root / "sheet.csv"
        with csv_path.open("w", encoding="utf-8", newline="") as handle:
            writer = csv.DictWriter(
                handle, fieldnames=["account", "platform", "data_permission"]
            )
            writer.writeheader()
            writer.writerows(rows)
        state_path = self.root / "state.json"
        state_path.write_text(json.dumps(state or self.state), encoding="utf-8")
        args = SimpleNamespace(
            sheet_csv=str(csv_path),
            state_json=str(state_path),
            output=str(self.root / "plan.json"),
            account_col="account",
            platform_col="platform",
            permission_col="data_permission",
            sync_mode=sync_mode,
            new_member_role=roles or [],
            allow_unknown_platform=allow_unknown_platform,
        )
        return build_plan(args)

    @staticmethod
    def standard_rows() -> list[dict[str, str]]:
        return [
            {"account": "alice@example.com", "platform": "iOS", "data_permission": "iOS Data"},
            {"account": "alice@example.com", "platform": "iOS", "data_permission": "iOS Data"},
            {"account": "bob@example.com", "platform": "Android", "data_permission": "Android Data"},
            {"account": "carol@example.com", "platform": "iOS", "data_permission": "iOS Data"},
        ]

    def test_additive_preserves_roles_and_unrelated_permissions(self) -> None:
        plan = self.plan(self.standard_rows(), roles=["member"])
        self.assertEqual(plan["status"], "READY_FOR_APPROVAL")
        self.assertEqual(plan["source"]["deduplicated_rows"], 1)
        self.assertEqual(len(plan["member_actions"]), 1)
        self.assertEqual(plan["member_actions"][0]["action"], "ADD_PROJECT_MEMBER")
        self.assertTrue(
            all(not item.get("permission_removals") for item in plan["member_actions"])
        )
        bob = next(item for item in plan["unchanged_accounts"] if item["account"].startswith("bob"))
        self.assertEqual(bob["role_names"], ["admin"])
        self.assertEqual(bob["data_permission_names"], ["Android Data", "Legacy Data"])

    def test_exact_mode_plans_reviewable_removal(self) -> None:
        plan = self.plan(self.standard_rows(), sync_mode="exact", roles=["member"])
        bob = next(item for item in plan["member_actions"] if item["account"].startswith("bob"))
        self.assertEqual(bob["permission_removals"], ["Legacy Data"])
        self.assertEqual(bob["current_role_names"], bob["target_role_names"])

    def test_existing_role_order_is_preserved(self) -> None:
        state = json.loads(json.dumps(self.state))
        state["members"][0]["role_names"] = ["member", "analyst"]
        rows = [
            {
                "account": "alice@example.com",
                "platform": "Android",
                "data_permission": "Android Data",
            }
        ]
        plan = self.plan(rows, state=state)
        action = plan["member_actions"][0]
        self.assertEqual(action["current_role_names"], ["member", "analyst"])
        self.assertEqual(action["target_role_names"], ["member", "analyst"])

    def test_invalid_candidate_user_id_blocks_without_action(self) -> None:
        state = json.loads(json.dumps(self.state))
        state["candidates"][0]["user_id"] = None
        rows = [
            {
                "account": "carol@example.com",
                "platform": "iOS",
                "data_permission": "iOS Data",
            }
        ]
        plan = self.plan(rows, state=state, roles=["member"])
        self.assertEqual(plan["status"], "BLOCKED")
        self.assertIn(
            "INVALID_CANDIDATE_USER_ID", {item["code"] for item in plan["blockers"]}
        )
        self.assertEqual(plan["member_actions"], [])

    def test_invalid_existing_member_user_id_blocks_without_action(self) -> None:
        state = json.loads(json.dumps(self.state))
        state["members"][0]["user_id"] = 0
        rows = [
            {
                "account": "alice@example.com",
                "platform": "Android",
                "data_permission": "Android Data",
            }
        ]
        plan = self.plan(rows, state=state)
        self.assertEqual(plan["status"], "BLOCKED")
        self.assertIn(
            "INVALID_MEMBER_USER_ID", {item["code"] for item in plan["blockers"]}
        )
        self.assertEqual(plan["member_actions"], [])

    def test_invalid_existing_roles_block_without_action(self) -> None:
        state = json.loads(json.dumps(self.state))
        state["members"][0]["role_names"] = []
        rows = [
            {
                "account": "alice@example.com",
                "platform": "Android",
                "data_permission": "Android Data",
            }
        ]
        plan = self.plan(rows, state=state)
        self.assertEqual(plan["status"], "BLOCKED")
        self.assertIn("INVALID_MEMBER_ROLES", {item["code"] for item in plan["blockers"]})
        self.assertEqual(plan["member_actions"], [])

    def test_unknown_platform_blocks_by_default(self) -> None:
        rows = [
            {"account": "alice@example.com", "platform": "iSO", "data_permission": "Typo Data"}
        ]
        plan = self.plan(rows)
        self.assertEqual(plan["status"], "BLOCKED")
        self.assertIn("BLOCKED_UNKNOWN_PLATFORM", {item["code"] for item in plan["blockers"]})

    def test_permission_platform_conflict_blocks(self) -> None:
        rows = [
            {"account": "alice@example.com", "platform": "iOS", "data_permission": "Mobile Data"},
            {"account": "bob@example.com", "platform": "Android", "data_permission": "Mobile Data"},
        ]
        plan = self.plan(rows)
        self.assertEqual(plan["status"], "BLOCKED")
        self.assertIn("PERMISSION_PLATFORM_CONFLICT", {item["code"] for item in plan["blockers"]})

    def test_shared_definition_update_is_disclosed(self) -> None:
        state = json.loads(json.dumps(self.state))
        state["data_powers"][0]["platform"] = "Android"
        state["data_powers"][0]["member_accounts"] = [
            "alice@example.com",
            "outside@example.com",
        ]
        rows = [
            {"account": "alice@example.com", "platform": "iOS", "data_permission": "iOS Data"}
        ]
        plan = self.plan(rows, state=state)
        action = plan["data_permission_actions"][0]
        self.assertEqual(action["action"], "UPDATE_DATA_PERMISSION")
        self.assertEqual(action["out_of_scope_member_count"], 1)
        self.assertIn("SHARED_PERMISSION_UPDATE", {item["code"] for item in plan["risk_flags"]})

    def test_final_state_is_idempotent(self) -> None:
        state = json.loads(json.dumps(self.state))
        state["members"][1]["data_power_ids"] = [11]
        state["members"].append(
            {
                "account": "carol@example.com",
                "user_id": 503,
                "role_names": ["member"],
                "data_power_ids": [10],
            }
        )
        plan = self.plan(self.standard_rows(), state=state, sync_mode="exact", roles=["member"])
        self.assertEqual(plan["status"], "NO_CHANGE")
        self.assertEqual(plan["summary"]["data_permission_actions"], 0)
        self.assertEqual(plan["summary"]["member_actions"], 0)


if __name__ == "__main__":
    unittest.main(verbosity=2)

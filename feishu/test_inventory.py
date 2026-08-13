import json
import tempfile
import unittest
from pathlib import Path

import inventory


ROOTS = [
    {"type": "wiki_space", "id": "s1", "title": "TikTok Ops"},
    {"type": "drive_folder", "id": "folder1", "title": "Shared Business"},
    {"type": "bitable", "id": "base2", "title": "Known Base"},
]


class FakeClient:
    def __init__(self, fail_wiki_children=False, empty_drive=False):
        self.fail_wiki_children = fail_wiki_children
        self.empty_drive = empty_drive
        self.calls = []

    def get_json(self, path, token, query=None):
        query = query or {}
        self.calls.append((path, query))
        if path == "/wiki/v2/spaces/get_node":
            return {"code": 0, "data": {"node": {
                "space_id": "s1", "node_token": "n1", "obj_token": "doc1",
                "obj_type": "docx", "title": "TikTok SOP", "has_child": True,
            }}}
        if path == "/wiki/v2/spaces/s1/nodes":
            if self.fail_wiki_children:
                return {"code": 131006, "msg": "permission denied"}
            if query.get("parent_node_token") == "n1":
                return {"code": 0, "data": {"items": [{
                    "node_token": "n2", "obj_token": "base1", "obj_type": "bitable",
                    "title": "直播运营", "has_child": True,
                }]}}
            if query.get("parent_node_token") == "n2":
                return {"code": 0, "data": {"items": [{
                    "node_token": "n3", "obj_token": "doc3", "obj_type": "docx",
                    "title": "SOP", "has_child": False,
                }]}}
            return {"code": 0, "data": {"items": [{
                "node_token": "n1", "obj_token": "doc1", "obj_type": "docx",
                "title": "TikTok SOP", "has_child": True,
            }]}}
        if path == "/drive/v1/files":
            if self.empty_drive:
                return {"code": 0, "data": {"files": []}}
            if query.get("folder_token") == "folder2":
                return {"code": 0, "data": {"files": [{
                    "token": "sheet1", "type": "sheet", "name": "Finance  Final", "modified_time": "1",
                }]}}
            self.assert_configured_folder(query)
            return {"code": 0, "data": {"files": [{
                "token": "folder2", "type": "folder", "name": "奈杜合作",
            }]}}
        if path in {"/bitable/v1/apps/base1/tables", "/bitable/v1/apps/base2/tables"}:
            suffix = "1" if "base1" in path else "2"
            return {"code": 0, "data": {"items": [{"table_id": f"tbl{suffix}", "name": "选品"}]}}
        raise AssertionError(path)

    def assert_configured_folder(self, query):
        if query.get("folder_token") != "folder1":
            raise AssertionError("Drive listing must always name a configured folder")


class InventoryTests(unittest.TestCase):
    def test_wiki_page_size_is_official_maximum_50(self):
        client = FakeClient()
        inventory.InventoryBuilder(client, "token", [ROOTS[0]]).build()
        wiki_calls = [query for path, query in client.calls if path.endswith("/nodes")]
        self.assertTrue(wiki_calls)
        self.assertTrue(all(query["page_size"] == 50 for query in wiki_calls))

    def test_configured_wiki_space_recurses_and_finds_nested_base(self):
        result = inventory.InventoryBuilder(FakeClient(), "token", [ROOTS[0]]).build()
        nested = next(r for r in result["resources"] if r["resource_id"] == "doc3")
        self.assertEqual(nested["location_path"], "TikTok Ops/TikTok SOP/直播运营/SOP")
        self.assertTrue(any(r["resource_type"] == "bitable_table" for r in result["resources"]))

    def test_configured_wiki_node_recurses_from_subtree_only(self):
        root = {"type": "wiki_node", "id": "n1", "title": "Operations"}
        client = FakeClient()
        result = inventory.InventoryBuilder(client, "token", [root]).build()
        self.assertTrue(any(r["resource_id"] == "doc3" for r in result["resources"]))
        calls = [query for path, query in client.calls if path.endswith("/nodes")]
        self.assertEqual(calls[0]["parent_node_token"], "n1")

    def test_configured_drive_folder_recurses_without_app_root(self):
        client = FakeClient()
        result = inventory.InventoryBuilder(client, "token", [ROOTS[1]]).build()
        sheet = next(r for r in result["resources"] if r["resource_id"] == "sheet1")
        self.assertEqual(sheet["location_path"], "Shared Business/奈杜合作/Finance  Final")
        drive_queries = [q for path, q in client.calls if path == "/drive/v1/files"]
        self.assertTrue(all(q.get("folder_token") for q in drive_queries))
        self.assertTrue(all(q["page_size"] == 200 for q in drive_queries))

    def test_empty_configured_drive_root_is_not_full_workspace_coverage(self):
        result = inventory.InventoryBuilder(FakeClient(empty_drive=True), "token", [ROOTS[1]]).build()
        self.assertEqual(result["summary"]["coverage_status"], "partial")
        self.assertTrue(any(item["status"] == "empty_root" for item in result["coverage"]))
        self.assertTrue(any(item["status"] == "unsupported_global_discovery" for item in result["coverage"]))

    def test_partial_failure_continues_other_roots_and_reports_permission(self):
        result = inventory.InventoryBuilder(FakeClient(fail_wiki_children=True), "token", ROOTS).build()
        self.assertTrue(any(r["resource_id"] == "sheet1" for r in result["resources"]))
        self.assertTrue(any(r["resource_id"] == "base2" for r in result["resources"]))
        statuses = {item["status"] for item in result["coverage"]}
        self.assertIn("permission_denied", statuses)
        self.assertIn("partial_coverage", statuses)
        self.assertEqual(result["summary"]["coverage_status"], "partial")

    def test_no_roots_makes_no_discovery_calls_and_claims_partial_coverage(self):
        client = FakeClient()
        result = inventory.InventoryBuilder(client, "token", []).build()
        self.assertEqual(client.calls, [])
        self.assertEqual(result["summary"]["total_resources"], 0)
        self.assertEqual(result["summary"]["coverage_status"], "partial")

    def test_known_bitable_root_lists_tables(self):
        result = inventory.InventoryBuilder(FakeClient(), "token", [ROOTS[2]]).build()
        self.assertEqual(result["summary"]["counts_by_type"], {"bitable": 1, "bitable_table": 1})

    def test_root_manifest_validation(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "roots.json"
            path.write_text(json.dumps({"roots": ROOTS}), encoding="utf-8")
            self.assertEqual(inventory.load_roots(path), ROOTS)
            path.write_text(json.dumps({"roots": [{"type": "unknown", "id": "x"}]}), encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "unsupported type"):
                inventory.load_roots(path)

    def test_report_contains_explicit_coverage_states_and_is_safe(self):
        result = inventory.InventoryBuilder(FakeClient(empty_drive=True), "token", [ROOTS[1]]).build()
        report = inventory.render_report(result)
        for text in ("Coverage status", "empty_root", "unsupported_global_discovery", "partial", "AI retrieval"):
            self.assertIn(text, report)
        self.assertNotIn("tenant_access_token", report)
        self.assertNotIn("Authorization", report)


if __name__ == "__main__":
    unittest.main()

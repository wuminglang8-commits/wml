import unittest

import inventory


class FakeClient:
    def __init__(self, fail_drive=False, fail_wiki_spaces=False):
        self.fail_drive = fail_drive
        self.fail_wiki_spaces = fail_wiki_spaces
        self.calls = []

    def get_json(self, path, token, query=None):
        self.calls.append((path, query or {}))
        if path == "/wiki/v2/spaces":
            if self.fail_wiki_spaces:
                return {"code": 99902, "msg": "space listing unavailable"}
            return {"code": 0, "data": {"items": [{"space_id": "s1", "name": "TikTok Ops"}]}}
        if path == "/wiki/v2/spaces/get_node":
            return {"code": 0, "data": {"node": {
                "space_id": "s1", "node_token": "anchor", "obj_token": "base1",
                "obj_type": "bitable", "title": "Known Base", "has_child": False,
            }}}
        if path == "/wiki/v2/spaces/s1/nodes":
            if (query or {}).get("parent_node_token") == "n1":
                return {"code": 0, "data": {"items": [{
                    "node_token": "n2", "obj_token": "doc2", "obj_type": "docx",
                    "title": "SOP", "has_child": False,
                }]}}
            return {"code": 0, "data": {"items": [{
                "node_token": "n1", "obj_token": "base1", "obj_type": "bitable",
                "title": "直播运营", "has_child": True,
            }]}}
        if path == "/drive/v1/files":
            if self.fail_drive:
                return {"code": 99901, "msg": "permission denied"}
            if (query or {}).get("folder_token") == "folder1":
                return {"code": 0, "data": {"files": [{
                    "token": "sheet1", "type": "sheet", "name": "Finance  Final", "modified_time": "1"
                }]}}
            return {"code": 0, "data": {"files": [{
                "token": "folder1", "type": "folder", "name": "奈杜合作"
            }, {"token": "duplicate", "type": "docx", "name": "SOP"}]}}
        if path == "/bitable/v1/apps/base1/tables":
            return {"code": 0, "data": {"items": [{"table_id": "tbl1", "name": "选品"}]}}
        raise AssertionError(path)


class InventoryTests(unittest.TestCase):
    def test_inventory_discovers_hierarchy_types_and_tables(self):
        result = inventory.InventoryBuilder(FakeClient(), "token").build()
        self.assertEqual(result["schema_version"], "1.0")
        self.assertEqual(result["summary"]["total_resources"], 7)
        self.assertEqual(result["summary"]["counts_by_type"]["bitable_table"], 1)
        sop = next(r for r in result["resources"] if r["resource_id"] == "doc2")
        self.assertEqual(sop["location_path"], "TikTok Ops/直播运营/SOP")
        self.assertIn("TikTok", sop["project_candidates"])

    def test_partial_failure_does_not_stop_other_discovery(self):
        result = inventory.InventoryBuilder(FakeClient(fail_drive=True), "token").build()
        self.assertGreater(result["summary"]["total_resources"], 0)
        self.assertEqual(result["summary"]["inaccessible_count"], 1)
        self.assertEqual(result["inaccessible"][0]["scope"], "drive:root")

    def test_configured_wiki_anchor_fallback_survives_space_listing_failure(self):
        result = inventory.InventoryBuilder(FakeClient(fail_wiki_spaces=True), "token").build()
        self.assertTrue(any(r["resource_id"] == "base1" for r in result["resources"]))
        self.assertTrue(any(r["resource_type"] == "bitable_table" for r in result["resources"]))
        self.assertTrue(any(i["scope"] == "wiki_spaces" for i in result["inaccessible"]))

    def test_duplicate_naming_and_classification_analysis(self):
        result = inventory.InventoryBuilder(FakeClient(), "token").build()
        self.assertTrue(any(item["normalized_title"] == "sop" for item in result["duplicate_candidates"]))
        self.assertTrue(any(item["reason"] == "inconsistent whitespace" for item in result["naming_inconsistencies"]))
        folder = next(r for r in result["resources"] if r["resource_id"] == "folder1")
        self.assertEqual(folder["related_entity_candidates"], ["Naidu / 奈杜"])

    def test_report_is_safe_and_contains_required_sections(self):
        result = inventory.InventoryBuilder(FakeClient(), "token").build()
        report = inventory.render_report(result)
        for heading in ("Resources by type", "Major information clusters", "Inaccessible", "Duplicate", "AI retrieval"):
            self.assertIn(heading, report)
        self.assertNotIn("tenant_access_token", report)
        self.assertNotIn("Authorization", report)


if __name__ == "__main__":
    unittest.main()

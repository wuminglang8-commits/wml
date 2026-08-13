#!/usr/bin/env python3
"""Read-only Feishu Knowledge Roots inventory and safe report generator."""

from __future__ import annotations

import argparse
import json
import os
import re
from collections import Counter, defaultdict, deque
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Optional

from connector import AuthenticationError, ConnectorError, FeishuConnector


SCHEMA_VERSION = "1.1"
ROOT_TYPES = {"wiki_space", "wiki_node", "drive_folder", "bitable"}
TYPE_MAP = {
    "doc": "doc", "docx": "docx", "sheet": "sheet", "bitable": "bitable",
    "folder": "folder", "file": "file", "mindnote": "mindnote", "slides": "slides",
}
KEYWORDS = {
    "business_category_candidates": {
        "company operations": ["运营", "operation", "管理"],
        "livestream operations": ["直播", "livestream"],
        "video operations": ["视频", "video"],
        "product selection / procurement": ["选品", "采购", "procurement"],
        "payment / finance": ["付款", "支付", "财务", "finance", "payment"],
        "contracts / external cooperation": ["合同", "合作", "contract"],
        "SOP / training": ["sop", "培训", "training"],
        "strategy / research": ["战略", "研究", "strategy", "research"],
        "historical decisions": ["决策", "复盘", "历史", "decision"],
    },
    "project_candidates": {
        "TikTok": ["tiktok"], "Shopify / independent site": ["shopify", "独立站"],
        "press-on nails": ["穿戴甲", "press-on", "press on"],
        "school cooperation": ["学校", "school"],
        "Feishu / internal systems": ["飞书", "feishu", "内部系统"],
        "TikTok AM / POP applications": ["tiktok am", "pop 申请", "pop申请"],
    },
    "department_candidates": {
        "operations": ["运营", "operation"], "finance": ["财务", "finance"],
        "procurement": ["采购", "procurement"], "training": ["培训", "training"],
    },
    "related_entity_candidates": {"Naidu / 奈杜": ["奈杜", "naidu"]},
}


@dataclass
class Resource:
    title: str
    resource_type: str
    location_path: str
    parent_id: Optional[str]
    parent_title: Optional[str]
    resource_id: str
    source_scope: str
    last_modified_at: Optional[str] = None
    business_category_candidates: list[str] = field(default_factory=list)
    project_candidates: list[str] = field(default_factory=list)
    department_candidates: list[str] = field(default_factory=list)
    related_entity_candidates: list[str] = field(default_factory=list)
    classification_confidence: float = 0.0
    classification_status: str = "unclassified"
    access_status: str = "accessible"
    error: Optional[dict[str, Any]] = None
    provenance: dict[str, Any] = field(default_factory=dict)


def load_roots(path: Path) -> list[dict[str, str]]:
    """Load and validate a local root manifest without logging its identifiers."""
    try:
        document = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise ValueError(f"cannot read Knowledge Roots file: {exc}") from None
    roots = document.get("roots") if isinstance(document, dict) else None
    if not isinstance(roots, list):
        raise ValueError("Knowledge Roots file must contain a roots array")
    normalized = []
    for position, root in enumerate(roots, 1):
        if not isinstance(root, dict) or root.get("type") not in ROOT_TYPES:
            raise ValueError(f"Knowledge Root {position} has an unsupported type")
        if not isinstance(root.get("id"), str) or not root["id"].strip():
            raise ValueError(f"Knowledge Root {position} requires a non-empty id")
        normalized.append({
            "type": root["type"], "id": root["id"].strip(),
            "title": str(root.get("title") or f"Configured {root['type']}").strip(),
        })
    return normalized


class InventoryBuilder:
    def __init__(self, client: FeishuConnector, token: str, roots: list[dict[str, str]]):
        self.client = client
        self.token = token
        self.roots = roots
        self.resources: list[Resource] = []
        self.coverage: list[dict[str, Any]] = [{
            "scope": "global_discovery", "status": "unsupported_global_discovery",
            "message": "Tenant application roots are not a complete workspace index; only configured Knowledge Roots are scanned.",
        }]
        self._resource_keys: set[tuple[str, str]] = set()

    def _add(self, resource: Resource) -> None:
        key = (resource.resource_type, resource.resource_id)
        if key not in self._resource_keys:
            self._resource_keys.add(key)
            self.resources.append(resource)

    @staticmethod
    def _failure_status(code: Any, message: str) -> str:
        text = message.casefold()
        return "permission_denied" if code in {99991663, 131006} or "permission" in text else "inaccessible"

    def _record(self, scope: str, status: str, message: str, code: Any = None) -> None:
        item = {"scope": scope, "status": status, "message": message}
        if code is not None:
            item["feishu_code"] = code
        self.coverage.append(item)

    def _get(self, scope: str, path: str, query: Optional[dict[str, Any]] = None) -> Optional[dict[str, Any]]:
        try:
            response = self.client.get_json(path, self.token, query)
            if response.get("code", 0) != 0:
                message = response.get("msg", "Feishu API error")
                self._record(scope, self._failure_status(response.get("code"), message), message, response.get("code"))
                return None
            return response.get("data", {})
        except ConnectorError as exc:
            message = str(exc)
            self._record(scope, self._failure_status(None, message), message)
            return None

    def _pages(self, scope: str, path: str, item_key: str, page_size: int,
               query: Optional[dict[str, Any]] = None):
        page_token = None
        while True:
            params = dict(query or {})
            params["page_size"] = page_size
            if page_token:
                params["page_token"] = page_token
            data = self._get(scope, path, params)
            if data is None:
                return
            yield from data.get(item_key, [])
            if not data.get("has_more"):
                return
            page_token = data.get("page_token")
            if not page_token:
                self._record(scope, "partial_coverage", "invalid pagination response")
                return

    def _scan_wiki_space(self, root: dict[str, str]) -> None:
        space_id, title = root["id"], root["title"]
        coverage_start = len(self.coverage)
        self._add(Resource(title, "wiki_space", title, None, None, space_id,
                           f"knowledge_root:wiki_space", provenance={"discovery": "configured-root"}))
        count = self._discover_wiki_nodes(space_id, title)
        self._finish_root(f"wiki_space:{title}", count, coverage_start)

    def _scan_wiki_node(self, root: dict[str, str]) -> None:
        scope = f"wiki_node:{root['title']}"
        coverage_start = len(self.coverage)
        data = self._get(scope, "/wiki/v2/spaces/get_node", {"token": root["id"]})
        if data is None:
            return
        node = data.get("node", {})
        obj_token = node.get("obj_token")
        node_token = node.get("node_token") or root["id"]
        space_id = node.get("space_id")
        if not obj_token or not space_id:
            self._record(scope, "inaccessible", "Wiki root resolution returned incomplete metadata")
            return
        title = node.get("title") or root["title"]
        self._add(Resource(
            title, TYPE_MAP.get(node.get("obj_type"), node.get("obj_type") or "unknown"), title,
            node.get("parent_node_token"), None, obj_token, "knowledge_root:wiki_node",
            provenance={"api": "wiki/v2/spaces/get_node", "node_token": node_token,
                        "discovery": "configured-root"},
        ))
        count = 1
        if node.get("has_child"):
            count += self._discover_wiki_nodes(str(space_id), title, (node_token, title, title))
        self._finish_root(scope, count, coverage_start)

    def _discover_wiki_nodes(self, space_id: str, space_title: str,
                             initial_parent: Optional[tuple[str, str, str]] = None) -> int:
        queue = deque([initial_parent or (None, space_title, space_title)])
        seen: set[str] = set()
        count = 0
        while queue:
            parent_node, parent_path, parent_title = queue.popleft()
            query = {"parent_node_token": parent_node} if parent_node else {}
            scope = f"wiki_nodes:{space_title}:{parent_title}"
            for node in self._pages(scope, f"/wiki/v2/spaces/{space_id}/nodes", "items", 50, query):
                node_token = node.get("node_token")
                if not node_token or node_token in seen:
                    continue
                seen.add(node_token)
                title = node.get("title") or "Untitled"
                resource_type = TYPE_MAP.get(node.get("obj_type"), node.get("obj_type") or "unknown")
                resource_id = node.get("obj_token") or node_token
                path = f"{parent_path}/{title}"
                self._add(Resource(
                    title, resource_type, path, parent_node or space_id, parent_title,
                    resource_id, f"wiki:{space_id}",
                    provenance={"api": "wiki/v2/spaces/:space_id/nodes", "node_token": node_token},
                ))
                count += 1
                if node.get("has_child"):
                    queue.append((node_token, path, title))
        return count

    def _scan_drive_folder(self, root: dict[str, str]) -> None:
        root_id, title = root["id"], root["title"]
        coverage_start = len(self.coverage)
        self._add(Resource(title, "folder", title, None, None, root_id,
                           "knowledge_root:drive_folder", provenance={"discovery": "configured-root"}))
        queue = deque([(root_id, title, title)])
        seen = {root_id}
        count = 0
        while queue:
            folder_token, parent_path, parent_title = queue.popleft()
            scope = f"drive_folder:{parent_title}"
            for item in self._pages(scope, "/drive/v1/files", "files", 200,
                                    {"folder_token": folder_token}):
                token = item.get("token")
                if not token or token in seen:
                    continue
                seen.add(token)
                title = item.get("name") or "Untitled"
                resource_type = TYPE_MAP.get(item.get("type"), item.get("type") or "unknown")
                path = f"{parent_path}/{title}"
                self._add(Resource(
                    title, resource_type, path, folder_token, parent_title, token,
                    "knowledge_root:drive_folder", _timestamp(item.get("modified_time")),
                    provenance={"api": "drive/v1/files"},
                ))
                count += 1
                if resource_type == "folder":
                    queue.append((token, path, title))
        self._finish_root(f"drive_folder:{root['title']}", count, coverage_start)

    def _scan_bitable(self, root: dict[str, str]) -> None:
        coverage_start = len(self.coverage)
        self._add(Resource(root["title"], "bitable", root["title"], None, None, root["id"],
                           "knowledge_root:bitable", provenance={"discovery": "configured-root"}))
        count = self._discover_bitable_tables(root["id"], root["title"], root["title"],
                                              "knowledge_root:bitable")
        self._finish_root(f"bitable:{root['title']}", count, coverage_start)

    def _discover_bitable_tables(self, app_token: str, title: str, path: str, source_scope: str) -> int:
        count = 0
        for table in self._pages(f"bitable_tables:{title}", f"/bitable/v1/apps/{app_token}/tables",
                                 "items", 100):
            table_id = table.get("table_id")
            if table_id:
                table_title = table.get("name") or "Untitled table"
                self._add(Resource(table_title, "bitable_table", f"{path}/{table_title}", app_token,
                                   title, table_id, source_scope,
                                   provenance={"api": "bitable/v1/apps/:app_token/tables"}))
                count += 1
        return count

    def _finish_root(self, scope: str, discovered_children: int, coverage_start: int) -> None:
        failures = [item for item in self.coverage[coverage_start:]
                    if item["status"] in {"inaccessible", "permission_denied", "partial_coverage"}]
        if discovered_children == 0 and not failures:
            self._record(scope, "empty_root", "Configured root is accessible but contains no discoverable children")
        elif failures:
            self._record(scope, "partial_coverage", "Root scan completed with inaccessible descendants")
        else:
            self._record(scope, "discovered", f"Discovered {discovered_children} child resources")

    def discover_roots(self) -> None:
        if not self.roots:
            self._record("knowledge_roots", "partial_coverage", "No Knowledge Roots are configured")
            return
        handlers = {
            "wiki_space": self._scan_wiki_space, "wiki_node": self._scan_wiki_node,
            "drive_folder": self._scan_drive_folder, "bitable": self._scan_bitable,
        }
        for root in self.roots:
            handlers[root["type"]](root)

        # Bases found under Wiki/Drive also receive read-only table discovery.
        configured = {root["id"] for root in self.roots if root["type"] == "bitable"}
        for base in list(self.resources):
            if base.resource_type == "bitable" and base.resource_id not in configured:
                self._discover_bitable_tables(base.resource_id, base.title, base.location_path, base.source_scope)

    def classify(self) -> None:
        for resource in self.resources:
            title_text, path_text = resource.title.casefold(), resource.location_path.casefold()
            best = 0.0
            for field_name, groups in KEYWORDS.items():
                matches = []
                for label, words in groups.items():
                    if any(word.casefold() in title_text for word in words):
                        matches.append(label); best = max(best, 0.9)
                    elif any(word.casefold() in path_text for word in words):
                        matches.append(label); best = max(best, 0.65)
                setattr(resource, field_name, matches)
            resource.classification_confidence = best
            resource.classification_status = "candidate" if best else "unclassified"

    def build(self) -> dict[str, Any]:
        self.discover_roots()
        self.classify()
        failures = [item for item in self.coverage if item["status"] in
                    {"inaccessible", "permission_denied", "empty_root", "partial_coverage"}]
        counts = dict(sorted(Counter(r.resource_type for r in self.resources).items()))
        clusters = Counter(candidate for r in self.resources for field_name in KEYWORDS
                           for candidate in getattr(r, field_name))
        return {
            "schema_version": SCHEMA_VERSION, "generated_at": datetime.now(timezone.utc).isoformat(),
            "mode": "read-only", "coverage_model": "configured_knowledge_roots",
            "summary": {
                "total_resources": len(self.resources), "counts_by_type": counts,
                "major_clusters": dict(clusters.most_common(20)),
                "configured_roots": len(self.roots), "coverage_status": "partial" if failures else "configured_roots_complete",
                "coverage_counts": dict(sorted(Counter(item["status"] for item in self.coverage).items())),
                "inaccessible_count": len(failures),
            },
            "resources": [asdict(resource) for resource in self.resources], "coverage": self.coverage,
            "inaccessible": failures, "duplicate_candidates": _duplicates(self.resources),
            "naming_inconsistencies": _naming_issues(self.resources),
            "retrieval_gaps": _retrieval_gaps(self.resources, failures),
        }


def _timestamp(value: Any) -> Optional[str]:
    if value in (None, ""): return None
    try: return datetime.fromtimestamp(int(value), timezone.utc).isoformat()
    except (TypeError, ValueError, OSError): return str(value)


def _normalized_title(title: str) -> str:
    return re.sub(r"[^\w\u4e00-\u9fff]+", "", title.casefold())


def _duplicates(resources: list[Resource]) -> list[dict[str, Any]]:
    groups: dict[str, list[Resource]] = defaultdict(list)
    for resource in resources:
        key = _normalized_title(resource.title)
        if key: groups[key].append(resource)
    return [{"normalized_title": key, "count": len(items), "resource_ids": [r.resource_id for r in items]}
            for key, items in sorted(groups.items()) if len(items) > 1]


def _naming_issues(resources: list[Resource]) -> list[dict[str, str]]:
    issues = []
    for resource in resources:
        title, reason = resource.title, None
        if title != title.strip() or re.search(r"\s{2,}", title): reason = "inconsistent whitespace"
        elif title.casefold() in {"untitled", "untitled table", "新建文档", "无标题"}: reason = "generic or missing title"
        elif re.search(r"(?:副本|copy|final)[-_ ]*\d*$", title, re.I): reason = "copy/version suffix may obscure canonical resource"
        if reason: issues.append({"resource_id": resource.resource_id, "title": title, "reason": reason})
    return issues


def _retrieval_gaps(resources: list[Resource], failures: list[dict[str, Any]]) -> list[dict[str, str]]:
    gaps = [{"scope": item["scope"], "reason": item.get("message", item["status"])} for item in failures]
    for resource in resources:
        if resource.resource_type == "unknown": gaps.append({"resource_id": resource.resource_id, "reason": "unknown resource type"})
        if not resource.location_path or (resource.parent_id and not resource.parent_title):
            gaps.append({"resource_id": resource.resource_id, "reason": "incomplete hierarchy context"})
        if resource.classification_status == "unclassified":
            gaps.append({"resource_id": resource.resource_id, "reason": "metadata insufficient for classification"})
    return gaps


def render_report(inventory: dict[str, Any]) -> str:
    summary = inventory["summary"]
    lines = ["# Feishu Knowledge Roots Inventory", "", "Mode: read-only",
             f"Coverage: {summary['coverage_status']}", f"Configured roots: {summary['configured_roots']}",
             f"Total discovered resources: {summary['total_resources']}", "", "## Resources by type"]
    lines.extend(f"- {kind}: {count}" for kind, count in summary["counts_by_type"].items())
    if not summary["counts_by_type"]: lines.append("- None discovered")
    lines += ["", "## Coverage status"]
    lines.extend(f"- {status}: {count}" for status, count in summary["coverage_counts"].items())
    lines += ["", "## Root and access results"]
    lines.extend(f"- {item['scope']} [{item['status']}]: {item['message']}" for item in inventory["coverage"])
    lines += ["", "## Major information clusters"]
    lines.extend(f"- {name}: {count}" for name, count in summary["major_clusters"].items())
    if not summary["major_clusters"]: lines.append("- No confident metadata-based clusters detected")
    lines += ["", "## Duplicate candidates", f"- Groups: {len(inventory['duplicate_candidates'])}",
              "", "## Naming inconsistencies", f"- Resources: {len(inventory['naming_inconsistencies'])}",
              "", "## AI retrieval gaps", f"- Findings: {len(inventory['retrieval_gaps'])}",
              "", "Generated without document bodies or record contents. Global workspace completeness is not claimed."]
    return "\n".join(lines) + "\n"


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--roots-file", default="feishu/knowledge-roots.json")
    parser.add_argument("--output-dir", default="feishu/inventory-output")
    args = parser.parse_args()
    app_id, app_secret = os.environ.get("FEISHU_APP_ID"), os.environ.get("FEISHU_APP_SECRET")
    if not app_id or not app_secret:
        raise SystemExit("error: FEISHU_APP_ID and FEISHU_APP_SECRET are required")
    try:
        roots = load_roots(Path(args.roots_file))
    except ValueError as exc:
        raise SystemExit(f"error: {exc}") from None
    client = FeishuConnector(app_id, app_secret)
    try:
        inventory = InventoryBuilder(client, client.authenticate(), roots).build()
    except AuthenticationError as exc:
        raise SystemExit(f"error: {exc}")
    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    (output_dir / "inventory.json").write_text(json.dumps(inventory, ensure_ascii=False, indent=2), encoding="utf-8")
    (output_dir / "inventory-report.md").write_text(render_report(inventory), encoding="utf-8")
    print(json.dumps({"mode": "read-only", **inventory["summary"]}, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

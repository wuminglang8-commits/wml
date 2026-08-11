#!/usr/bin/env python3
"""Read-only Feishu workspace inventory and safe report generator."""

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

from connector import AuthenticationError, ConnectorError, FeishuConnector, WIKI_NODE_TOKEN


SCHEMA_VERSION = "1.0"
TYPE_MAP = {
    "doc": "doc",
    "docx": "docx",
    "sheet": "sheet",
    "bitable": "bitable",
    "folder": "folder",
    "file": "file",
    "mindnote": "mindnote",
    "slides": "slides",
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
        "TikTok": ["tiktok"],
        "Shopify / independent site": ["shopify", "独立站"],
        "press-on nails": ["穿戴甲", "press-on", "press on"],
        "school cooperation": ["学校", "school"],
        "Feishu / internal systems": ["飞书", "feishu", "内部系统"],
        "TikTok AM / POP applications": ["tiktok am", "pop 申请", "pop申请"],
    },
    "department_candidates": {
        "operations": ["运营", "operation"],
        "finance": ["财务", "finance"],
        "procurement": ["采购", "procurement"],
        "training": ["培训", "training"],
    },
    "related_entity_candidates": {
        "Naidu / 奈杜": ["奈杜", "naidu"],
    },
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


class InventoryBuilder:
    def __init__(self, client: FeishuConnector, token: str):
        self.client = client
        self.token = token
        self.resources: list[Resource] = []
        self.inaccessible: list[dict[str, Any]] = []

    def _get(self, scope: str, path: str, query: Optional[dict[str, Any]] = None) -> Optional[dict[str, Any]]:
        try:
            data = self.client.get_json(path, self.token, query)
            if data.get("code", 0) != 0:
                self.inaccessible.append({
                    "scope": scope,
                    "status": "inaccessible",
                    "feishu_code": data.get("code"),
                    "message": data.get("msg", "Feishu API error"),
                })
                return None
            return data.get("data", {})
        except ConnectorError as exc:
            self.inaccessible.append({"scope": scope, "status": "inaccessible", "message": str(exc)})
            return None

    def _pages(self, scope: str, path: str, item_key: str, query: Optional[dict[str, Any]] = None):
        page_token = None
        while True:
            params = dict(query or {})
            params.setdefault("page_size", 100)
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
                self.inaccessible.append({
                    "scope": scope, "status": "partial", "message": "invalid pagination response"
                })
                return

    def discover_wiki(self) -> None:
        discovered_spaces = 0
        for space in self._pages("wiki_spaces", "/wiki/v2/spaces", "items"):
            discovered_spaces += 1
            space_id = str(space.get("space_id", ""))
            title = space.get("name") or "Untitled Wiki space"
            self.resources.append(Resource(
                title=title, resource_type="wiki_space", location_path=title,
                parent_id=None, parent_title=None, resource_id=space_id,
                source_scope="wiki", provenance={"api": "wiki/v2/spaces"},
            ))
            self._discover_wiki_nodes(space_id, title)
        if not discovered_spaces:
            self._discover_configured_wiki_anchor()

    def _discover_configured_wiki_anchor(self) -> None:
        data = self._get(
            "configured_wiki_node",
            "/wiki/v2/spaces/get_node",
            {"token": WIKI_NODE_TOKEN},
        )
        if data is None:
            return
        node = data.get("node", {})
        node_token = node.get("node_token") or WIKI_NODE_TOKEN
        obj_token = node.get("obj_token")
        if not obj_token:
            self.inaccessible.append({
                "scope": "configured_wiki_node",
                "status": "partial",
                "message": "Wiki node response did not include a resource token",
            })
            return
        title = node.get("title") or "Configured Wiki resource"
        resource_type = TYPE_MAP.get(node.get("obj_type"), node.get("obj_type") or "unknown")
        self.resources.append(Resource(
            title=title,
            resource_type=resource_type,
            location_path=f"Configured Wiki/{title}",
            parent_id=node.get("parent_node_token"),
            parent_title="Configured Wiki",
            resource_id=obj_token,
            source_scope=f"wiki:{node.get('space_id', 'configured')}",
            provenance={
                "api": "wiki/v2/spaces/get_node",
                "node_token": node_token,
                "discovery": "configured-anchor-fallback",
            },
        ))
        if node.get("has_child") and node.get("space_id"):
            self._discover_wiki_nodes(
                str(node["space_id"]),
                "Configured Wiki",
                initial_parent=(node_token, f"Configured Wiki/{title}", title),
            )

    def _discover_wiki_nodes(
        self,
        space_id: str,
        space_title: str,
        initial_parent: Optional[tuple[str, str, str]] = None,
    ) -> None:
        queue = deque([initial_parent or (None, space_title, None)])
        seen: set[str] = set()
        while queue:
            parent_node, parent_path, parent_title = queue.popleft()
            query = {"parent_node_token": parent_node} if parent_node else {}
            scope = f"wiki_nodes:{space_id}:{parent_node or 'root'}"
            for node in self._pages(scope, f"/wiki/v2/spaces/{space_id}/nodes", "items", query):
                node_token = node.get("node_token")
                if not node_token or node_token in seen:
                    continue
                seen.add(node_token)
                title = node.get("title") or "Untitled"
                obj_token = node.get("obj_token") or node_token
                resource_type = TYPE_MAP.get(node.get("obj_type"), node.get("obj_type") or "unknown")
                path = f"{parent_path}/{title}"
                self.resources.append(Resource(
                    title=title, resource_type=resource_type, location_path=path,
                    parent_id=parent_node or space_id, parent_title=parent_title or space_title,
                    resource_id=obj_token, source_scope=f"wiki:{space_id}",
                    provenance={"api": "wiki/v2/spaces/:space_id/nodes", "node_token": node_token},
                ))
                if node.get("has_child"):
                    queue.append((node_token, path, title))

    def discover_drive(self) -> None:
        queue = deque([(None, "Drive", None)])
        seen: set[str] = set()
        while queue:
            folder_token, parent_path, parent_title = queue.popleft()
            query = {"folder_token": folder_token} if folder_token else {}
            scope = f"drive:{folder_token or 'root'}"
            for item in self._pages(scope, "/drive/v1/files", "files", query):
                token = item.get("token")
                if not token or token in seen:
                    continue
                seen.add(token)
                title = item.get("name") or "Untitled"
                resource_type = TYPE_MAP.get(item.get("type"), item.get("type") or "unknown")
                path = f"{parent_path}/{title}"
                self.resources.append(Resource(
                    title=title, resource_type=resource_type, location_path=path,
                    parent_id=folder_token, parent_title=parent_title,
                    resource_id=token, source_scope="drive",
                    last_modified_at=_timestamp(item.get("modified_time")),
                    provenance={"api": "drive/v1/files"},
                ))
                if resource_type == "folder":
                    queue.append((token, path, title))

    def discover_bitable_tables(self) -> None:
        bases = [r for r in self.resources if r.resource_type == "bitable"]
        for base in bases:
            scope = f"bitable_tables:{base.resource_id}"
            for table in self._pages(
                scope, f"/bitable/v1/apps/{base.resource_id}/tables", "items"
            ):
                table_id = table.get("table_id")
                if not table_id:
                    continue
                title = table.get("name") or "Untitled table"
                self.resources.append(Resource(
                    title=title, resource_type="bitable_table",
                    location_path=f"{base.location_path}/{title}",
                    parent_id=base.resource_id, parent_title=base.title,
                    resource_id=table_id, source_scope=base.source_scope,
                    provenance={"api": "bitable/v1/apps/:app_token/tables"},
                ))

    def classify(self) -> None:
        for resource in self.resources:
            title_text = resource.title.casefold()
            path_text = resource.location_path.casefold()
            best = 0.0
            for field_name, groups in KEYWORDS.items():
                matches = []
                for label, words in groups.items():
                    if any(word.casefold() in title_text for word in words):
                        matches.append(label)
                        best = max(best, 0.9)
                    elif any(word.casefold() in path_text for word in words):
                        matches.append(label)
                        best = max(best, 0.65)
                setattr(resource, field_name, matches)
            resource.classification_confidence = best
            resource.classification_status = "candidate" if best else "unclassified"

    def build(self) -> dict[str, Any]:
        self.discover_wiki()
        self.discover_drive()
        self.discover_bitable_tables()
        self.classify()
        duplicates = _duplicates(self.resources)
        naming = _naming_issues(self.resources)
        retrieval = _retrieval_gaps(self.resources, self.inaccessible)
        counts = dict(sorted(Counter(r.resource_type for r in self.resources).items()))
        clusters = Counter(
            candidate
            for resource in self.resources
            for field_name in KEYWORDS
            for candidate in getattr(resource, field_name)
        )
        return {
            "schema_version": SCHEMA_VERSION,
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "mode": "read-only",
            "summary": {
                "total_resources": len(self.resources),
                "counts_by_type": counts,
                "major_clusters": dict(clusters.most_common(20)),
                "inaccessible_count": len(self.inaccessible),
            },
            "resources": [asdict(resource) for resource in self.resources],
            "inaccessible": self.inaccessible,
            "duplicate_candidates": duplicates,
            "naming_inconsistencies": naming,
            "retrieval_gaps": retrieval,
        }


def _timestamp(value: Any) -> Optional[str]:
    if value in (None, ""):
        return None
    try:
        return datetime.fromtimestamp(int(value), timezone.utc).isoformat()
    except (TypeError, ValueError, OSError):
        return str(value)


def _normalized_title(title: str) -> str:
    return re.sub(r"[^\w\u4e00-\u9fff]+", "", title.casefold())


def _duplicates(resources: list[Resource]) -> list[dict[str, Any]]:
    groups: dict[str, list[Resource]] = defaultdict(list)
    for resource in resources:
        key = _normalized_title(resource.title)
        if key:
            groups[key].append(resource)
    return [
        {"normalized_title": key, "count": len(items), "resource_ids": [r.resource_id for r in items]}
        for key, items in sorted(groups.items()) if len(items) > 1
    ]


def _naming_issues(resources: list[Resource]) -> list[dict[str, str]]:
    issues = []
    for resource in resources:
        title = resource.title
        reason = None
        if title != title.strip() or re.search(r"\s{2,}", title):
            reason = "inconsistent whitespace"
        elif title.casefold() in {"untitled", "untitled table", "新建文档", "无标题"}:
            reason = "generic or missing title"
        elif re.search(r"(?:副本|copy|final)[-_ ]*\d*$", title, re.I):
            reason = "copy/version suffix may obscure canonical resource"
        if reason:
            issues.append({"resource_id": resource.resource_id, "title": title, "reason": reason})
    return issues


def _retrieval_gaps(resources: list[Resource], inaccessible: list[dict[str, Any]]) -> list[dict[str, str]]:
    gaps = [{"scope": item["scope"], "reason": item.get("message", "inaccessible")} for item in inaccessible]
    for resource in resources:
        if resource.resource_type == "unknown":
            gaps.append({"resource_id": resource.resource_id, "reason": "unknown resource type"})
        if not resource.location_path or (resource.parent_id and not resource.parent_title):
            gaps.append({"resource_id": resource.resource_id, "reason": "incomplete hierarchy context"})
        if resource.classification_status == "unclassified":
            gaps.append({"resource_id": resource.resource_id, "reason": "metadata insufficient for classification"})
    return gaps


def render_report(inventory: dict[str, Any]) -> str:
    summary = inventory["summary"]
    lines = [
        "# Feishu Workspace Inventory",
        "",
        "Mode: read-only",
        f"Total accessible resources: {summary['total_resources']}",
        f"Inaccessible/partial scopes: {summary['inaccessible_count']}",
        "",
        "## Resources by type",
    ]
    lines.extend(f"- {kind}: {count}" for kind, count in summary["counts_by_type"].items())
    lines += ["", "## Major information clusters"]
    lines.extend(f"- {name}: {count}" for name, count in summary["major_clusters"].items())
    if not summary["major_clusters"]:
        lines.append("- No confident metadata-based clusters detected")
    lines += ["", "## Inaccessible or partial scopes"]
    lines.extend(
        f"- {item['scope']}: {item.get('message', item['status'])}"
        for item in inventory["inaccessible"]
    )
    if not inventory["inaccessible"]:
        lines.append("- None observed")
    lines += ["", "## Duplicate candidates", f"- Groups: {len(inventory['duplicate_candidates'])}"]
    lines += ["", "## Naming inconsistencies", f"- Resources: {len(inventory['naming_inconsistencies'])}"]
    lines += ["", "## AI retrieval gaps", f"- Findings: {len(inventory['retrieval_gaps'])}"]
    lines += ["", "Generated without document bodies or record contents."]
    return "\n".join(lines) + "\n"


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output-dir", default="feishu/inventory-output")
    args = parser.parse_args()
    app_id = os.environ.get("FEISHU_APP_ID")
    app_secret = os.environ.get("FEISHU_APP_SECRET")
    if not app_id or not app_secret:
        raise SystemExit("error: FEISHU_APP_ID and FEISHU_APP_SECRET are required")
    client = FeishuConnector(app_id, app_secret)
    try:
        token = client.authenticate()
        inventory = InventoryBuilder(client, token).build()
    except AuthenticationError as exc:
        raise SystemExit(f"error: {exc}")
    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    (output_dir / "inventory.json").write_text(
        json.dumps(inventory, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    (output_dir / "inventory-report.md").write_text(render_report(inventory), encoding="utf-8")
    print(json.dumps({"mode": "read-only", **inventory["summary"]}, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

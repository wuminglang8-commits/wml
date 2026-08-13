#!/usr/bin/env python3
"""Minimal, safe connector for the designated WML Feishu test table."""

from __future__ import annotations

import argparse
import json
import os
import sys
import urllib.error
import urllib.parse
import urllib.request
from dataclasses import dataclass
from typing import Any, Callable, Optional


API_ROOT = "https://open.feishu.cn/open-apis"
WIKI_NODE_TOKEN = "KH94wULvJi2VYIkjMsBcVEGnnzb"
TABLE_ID = "tblrjmvrmMmhgKcX"
VIEW_ID = "vewWmrbIk1"
CONNECTION_TEST_LABEL = "Codex connection test"


class ConnectorError(RuntimeError):
    """A safe, user-actionable connector error."""


class AuthenticationError(ConnectorError):
    pass


class WikiResolutionError(ConnectorError):
    pass


class TablePermissionError(ConnectorError):
    pass


class RecordOperationError(ConnectorError):
    pass


Transport = Callable[
    [str, str, dict[str, str], Optional[dict[str, Any]]], dict[str, Any]
]


def _http_transport(
    method: str,
    url: str,
    headers: dict[str, str],
    payload: Optional[dict[str, Any]],
) -> dict[str, Any]:
    data = json.dumps(payload).encode() if payload is not None else None
    request = urllib.request.Request(url, data=data, headers=headers, method=method)
    try:
        with urllib.request.urlopen(request, timeout=20) as response:
            return json.loads(response.read())
    except (urllib.error.HTTPError, urllib.error.URLError, TimeoutError, json.JSONDecodeError) as exc:
        # Deliberately omit response bodies and request headers: either may contain secrets.
        status = getattr(exc, "code", "network")
        raise ConnectorError(f"Feishu request failed (status: {status})") from None


def _require_success(data: dict[str, Any], error_type: type[ConnectorError], action: str) -> None:
    if data.get("code", 0) != 0:
        code = data.get("code", "unknown")
        raise error_type(f"{action} failed (Feishu code: {code})")


@dataclass
class FeishuConnector:
    app_id: str
    app_secret: str
    transport: Transport = _http_transport

    def _request(
        self,
        method: str,
        path: str,
        token: Optional[str] = None,
        payload: Optional[dict[str, Any]] = None,
        query: Optional[dict[str, Any]] = None,
    ) -> dict[str, Any]:
        url = f"{API_ROOT}{path}"
        if query:
            url += "?" + urllib.parse.urlencode(query)
        headers = {"Content-Type": "application/json; charset=utf-8"}
        if token:
            headers["Authorization"] = f"Bearer {token}"
        return self.transport(method, url, headers, payload)

    def get_json(
        self,
        path: str,
        token: str,
        query: Optional[dict[str, Any]] = None,
    ) -> dict[str, Any]:
        """Call a Feishu GET endpoint through the secret-safe transport."""
        return self._request("GET", path, token=token, query=query)

    def authenticate(self) -> str:
        try:
            data = self._request(
                "POST",
                "/auth/v3/tenant_access_token/internal",
                payload={"app_id": self.app_id, "app_secret": self.app_secret},
            )
        except ConnectorError as exc:
            raise AuthenticationError(str(exc)) from None
        _require_success(data, AuthenticationError, "Authentication")
        token = data.get("tenant_access_token")
        if not token:
            raise AuthenticationError("Authentication response did not contain a tenant access token")
        return token

    def resolve_wiki_node(self, token: str) -> str:
        try:
            data = self._request(
                "GET", "/wiki/v2/spaces/get_node", token=token, query={"token": WIKI_NODE_TOKEN}
            )
        except ConnectorError as exc:
            raise WikiResolutionError(str(exc)) from None
        _require_success(data, WikiResolutionError, "Wiki resolution")
        node = data.get("data", {}).get("node", {})
        app_token = node.get("obj_token")
        if node.get("obj_type") != "bitable" or not app_token:
            raise WikiResolutionError("Wiki node does not resolve to a Bitable")
        return app_token

    def validate_target_table(self, token: str, app_token: str) -> None:
        page_token: Optional[str] = None
        try:
            while True:
                query: dict[str, Any] = {"page_size": 100}
                if page_token:
                    query["page_token"] = page_token
                data = self._request(
                    "GET",
                    f"/bitable/v1/apps/{app_token}/tables",
                    token=token,
                    query=query,
                )
                _require_success(data, TablePermissionError, "Table listing")
                page = data.get("data", {})
                if any(item.get("table_id") == TABLE_ID for item in page.get("items", [])):
                    return
                if not page.get("has_more"):
                    raise TablePermissionError(
                        "Designated table was not found in the resolved Bitable"
                    )
                page_token = page.get("page_token")
                if not page_token:
                    raise TablePermissionError(
                        "Table listing returned an invalid pagination response"
                    )
        except TablePermissionError:
            raise
        except ConnectorError as exc:
            raise TablePermissionError(str(exc)) from None

    def list_records(self, token: str, app_token: str) -> list[dict[str, Any]]:
        records: list[dict[str, Any]] = []
        page_token: Optional[str] = None
        try:
            while True:
                query: dict[str, Any] = {"view_id": VIEW_ID, "page_size": 100}
                if page_token:
                    query["page_token"] = page_token
                data = self._request(
                    "GET",
                    f"/bitable/v1/apps/{app_token}/tables/{TABLE_ID}/records",
                    token=token,
                    query=query,
                )
                _require_success(data, TablePermissionError, "Table read")
                page = data.get("data", {})
                records.extend(page.get("items", []))
                if not page.get("has_more"):
                    return records
                page_token = page.get("page_token")
                if not page_token:
                    raise TablePermissionError("Table read returned an invalid pagination response")
        except TablePermissionError:
            raise
        except ConnectorError as exc:
            raise TablePermissionError(str(exc)) from None

    def _primary_field_name(self, token: str, app_token: str) -> str:
        try:
            data = self._request(
                "GET",
                f"/bitable/v1/apps/{app_token}/tables/{TABLE_ID}/fields",
                token=token,
                query={"page_size": 100},
            )
            _require_success(data, RecordOperationError, "Field lookup")
            for field in data.get("data", {}).get("items", []):
                if field.get("is_primary"):
                    return field["field_name"]
        except RecordOperationError:
            raise
        except ConnectorError as exc:
            raise RecordOperationError(str(exc)) from None
        raise RecordOperationError("Could not identify the table's primary field")

    def write_test(
        self, token: str, app_token: str, records: list[dict[str, Any]]
    ) -> tuple[str, str]:
        pending = next(
            (item for item in records if item.get("fields", {}).get("Status") == "Pending"),
            None,
        )
        try:
            if pending:
                record_id = pending.get("record_id")
                if not record_id:
                    raise RecordOperationError("Pending record has no record ID")
                data = self._request(
                    "PUT",
                    f"/bitable/v1/apps/{app_token}/tables/{TABLE_ID}/records/{record_id}",
                    token=token,
                    payload={"fields": {"Status": "Connected"}},
                )
                operation = "updated"
            else:
                primary_field = self._primary_field_name(token, app_token)
                data = self._request(
                    "POST",
                    f"/bitable/v1/apps/{app_token}/tables/{TABLE_ID}/records",
                    token=token,
                    payload={
                        "fields": {
                            primary_field: CONNECTION_TEST_LABEL,
                            "Status": "Connected",
                        }
                    },
                )
                operation = "created"
            _require_success(data, RecordOperationError, "Record write")
            record_id = data.get("data", {}).get("record", {}).get("record_id")
            if not record_id:
                raise RecordOperationError("Record write response did not contain a record ID")
            return operation, record_id
        except RecordOperationError:
            raise
        except ConnectorError as exc:
            raise RecordOperationError(str(exc)) from None


def safe_summary(records: list[dict[str, Any]]) -> dict[str, Any]:
    statuses = {"Pending": 0, "Connected": 0, "Other/unset": 0}
    for record in records:
        status = record.get("fields", {}).get("Status")
        key = status if status in ("Pending", "Connected") else "Other/unset"
        statuses[key] += 1
    return {"record_count": len(records), "status_counts": statuses}


def _validated_target_from_environment() -> None:
    expected = {
        "FEISHU_WIKI_NODE_TOKEN": WIKI_NODE_TOKEN,
        "FEISHU_TABLE_ID": TABLE_ID,
        "FEISHU_VIEW_ID": VIEW_ID,
    }
    for name, designated_value in expected.items():
        configured = os.environ.get(name, designated_value)
        if configured != designated_value:
            raise ConnectorError(f"{name} does not match the designated test target")


def run(write_test: bool = False, transport: Transport = _http_transport) -> dict[str, Any]:
    app_id = os.environ.get("FEISHU_APP_ID")
    app_secret = os.environ.get("FEISHU_APP_SECRET")
    if not app_id or not app_secret:
        raise AuthenticationError("FEISHU_APP_ID and FEISHU_APP_SECRET are required")
    _validated_target_from_environment()

    connector = FeishuConnector(app_id, app_secret, transport)
    token = connector.authenticate()
    app_token = connector.resolve_wiki_node(token)
    connector.validate_target_table(token, app_token)
    records = connector.list_records(token, app_token)
    result: dict[str, Any] = {
        "mode": "write-test" if write_test else "read-only",
        "wiki_resolved": True,
        **safe_summary(records),
    }
    if write_test:
        operation, record_id = connector.write_test(token, app_token, records)
        verified_records = connector.list_records(token, app_token)
        verified = any(
            record.get("record_id") == record_id
            and record.get("fields", {}).get("Status") == "Connected"
            for record in verified_records
        )
        if not verified:
            raise RecordOperationError("Write verification failed")
        result.update(
            {
                "write_operation": operation,
                "write_verified": True,
                **safe_summary(verified_records),
            }
        )
    return result


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--write-test",
        action="store_true",
        help="explicitly update/create and verify a record in the designated test table",
    )
    args = parser.parse_args()
    try:
        print(json.dumps(run(write_test=args.write_test), indent=2, sort_keys=True))
        return 0
    except ConnectorError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())

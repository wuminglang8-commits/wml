import os
import unittest
from unittest.mock import patch

import connector


class FakeTransport:
    def __init__(self, records=None):
        self.records = records if records is not None else []
        self.calls = []

    def __call__(self, method, url, headers, payload):
        self.calls.append((method, url, headers, payload))
        if "tenant_access_token" in url:
            return {"code": 0, "tenant_access_token": "test-tenant-token"}
        if "wiki/v2" in url:
            return {"code": 0, "data": {"node": {"obj_type": "bitable", "obj_token": "app-token"}}}
        if url.endswith("/fields?page_size=100"):
            return {
                "code": 0,
                "data": {"items": [{"field_name": "Name", "is_primary": True}]},
            }
        if method == "PUT":
            record_id = url.rsplit("/", 1)[-1]
            for record in self.records:
                if record["record_id"] == record_id:
                    record["fields"]["Status"] = "Connected"
            return {"code": 0, "data": {"record": {"record_id": record_id}}}
        if method == "POST" and url.endswith("/records"):
            record = {"record_id": "new-record", "fields": payload["fields"]}
            self.records.append(record)
            return {"code": 0, "data": {"record": record}}
        if method == "GET" and "/records?" in url:
            return {"code": 0, "data": {"items": self.records, "has_more": False}}
        raise AssertionError(f"Unexpected request: {method} {url}")


class ConnectorTests(unittest.TestCase):
    env = {"FEISHU_APP_ID": "app-id", "FEISHU_APP_SECRET": "app-secret"}

    def test_default_run_is_read_only_and_safe(self):
        fake = FakeTransport([{"record_id": "r1", "fields": {"Status": "Pending", "Secret": "private"}}])
        with patch.dict(os.environ, self.env, clear=True):
            result = connector.run(transport=fake)

        self.assertEqual(result["mode"], "read-only")
        self.assertEqual(result["record_count"], 1)
        self.assertNotIn("Secret", str(result))
        self.assertFalse(any(call[0] in ("PUT", "POST") and "/records" in call[1] for call in fake.calls))

    def test_write_test_updates_pending_record_and_verifies(self):
        fake = FakeTransport([{"record_id": "r1", "fields": {"Status": "Pending"}}])
        with patch.dict(os.environ, self.env, clear=True):
            result = connector.run(write_test=True, transport=fake)

        self.assertEqual(result["write_operation"], "updated")
        self.assertTrue(result["write_verified"])
        self.assertEqual(result["status_counts"]["Connected"], 1)

    def test_write_test_creates_marked_record_when_none_pending(self):
        fake = FakeTransport([])
        with patch.dict(os.environ, self.env, clear=True):
            result = connector.run(write_test=True, transport=fake)

        self.assertEqual(result["write_operation"], "created")
        self.assertEqual(fake.records[0]["fields"]["Name"], connector.CONNECTION_TEST_LABEL)
        self.assertTrue(result["write_verified"])

    def test_rejects_non_designated_target(self):
        env = {**self.env, "FEISHU_TABLE_ID": "another-table"}
        with patch.dict(os.environ, env, clear=True):
            with self.assertRaisesRegex(connector.ConnectorError, "designated test target"):
                connector.run(transport=FakeTransport())

    def test_authentication_error_is_distinct_and_does_not_leak_secret(self):
        def failed_auth(method, url, headers, payload):
            return {"code": 999, "msg": f"bad secret {payload.get('app_secret')}"}

        with patch.dict(os.environ, self.env, clear=True):
            with self.assertRaises(connector.AuthenticationError) as context:
                connector.run(transport=failed_auth)
        self.assertNotIn("app-secret", str(context.exception))

    def test_wiki_and_table_errors_are_distinct(self):
        def failed_wiki(method, url, headers, payload):
            if "tenant_access_token" in url:
                return {"code": 0, "tenant_access_token": "token"}
            return {"code": 123}

        with patch.dict(os.environ, self.env, clear=True):
            with self.assertRaises(connector.WikiResolutionError):
                connector.run(transport=failed_wiki)

        class FailedTable(FakeTransport):
            def __call__(self, method, url, headers, payload):
                if "/records?" in url:
                    return {"code": 1254302}
                return super().__call__(method, url, headers, payload)

        with patch.dict(os.environ, self.env, clear=True):
            with self.assertRaises(connector.TablePermissionError):
                connector.run(transport=FailedTable())

    def test_record_operation_error_is_distinct(self):
        class FailedWrite(FakeTransport):
            def __call__(self, method, url, headers, payload):
                if method == "PUT":
                    return {"code": 1254303}
                return super().__call__(method, url, headers, payload)

        fake = FailedWrite([{"record_id": "r1", "fields": {"Status": "Pending"}}])
        with patch.dict(os.environ, self.env, clear=True):
            with self.assertRaises(connector.RecordOperationError):
                connector.run(write_test=True, transport=fake)

    def test_credentials_and_authorization_are_not_in_error(self):
        def network_failure(method, url, headers, payload):
            raise connector.ConnectorError(
                "Feishu request failed (status: 403)"
            )

        with patch.dict(os.environ, self.env, clear=True):
            with self.assertRaises(connector.AuthenticationError) as context:
                connector.run(transport=network_failure)
        message = str(context.exception)
        self.assertNotIn("app-secret", message)
        self.assertNotIn("Authorization", message)


if __name__ == "__main__":
    unittest.main()

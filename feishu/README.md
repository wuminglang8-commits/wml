# Feishu Operations OS — Connector Test

This directory is the first real Codex execution project under the WML shared layer.

## Goal

Establish a minimal, safe connection from GitHub/Codex to Feishu Bitable before building any KPI or management system.

## Test target

- Feishu application: `WML AI Operations`
- App ID is provided at runtime through `FEISHU_APP_ID`.
- App Secret is provided at runtime through `FEISHU_APP_SECRET`.
- Wiki node token: `KH94wULvJi2VYIkjMsBcVEGnnzb`
- Table ID: `tblrjmvrmMmhgKcX`
- View ID: `vewWmrbIk1`

## V1 acceptance test

1. Obtain a tenant access token from Feishu using environment credentials.
2. Resolve the Wiki node to the underlying Bitable app token.
3. Read the target table metadata/records.
4. Print a safe summary of the connection and records without printing secrets or access tokens.
5. Support an explicit write-test mode that updates the test record Status from `Pending` to `Connected` or creates a clearly marked connection-test record if no suitable record exists.
6. Re-read the table and verify the write.

## Safety

- Never commit App Secret, tenant access token, or other credentials.
- Never log secrets or full authorization headers.
- V1 may only operate on the designated test Base/Table.
- No destructive actions.
- Default execution is read-only; writes require an explicit `--write-test` flag.

## Setup and run

Python 3.9 or newer is required. The connector uses only the Python standard
library.

Set credentials in your shell (or copy `.env.example` to a local `.env` and
load it with your preferred environment tool). The connector intentionally does
not read `.env` itself.

```bash
export FEISHU_APP_ID='your_app_id'
export FEISHU_APP_SECRET='your_app_secret'
python3 feishu/connector.py
```

The default command is read-only. Its JSON output contains only the mode,
resolution result, record count, and aggregate counts for `Pending`,
`Connected`, and other/unset statuses. It never prints credentials, tokens,
authorization headers, app tokens, record IDs, or arbitrary record fields.
Before reading records, it uses Feishu's official list-tables endpoint to
confirm that the designated table belongs to the Bitable resolved from Wiki.

To perform the narrowly scoped connection test:

```bash
python3 feishu/connector.py --write-test
```

This explicit mode updates the first record whose `Status` is exactly
`Pending` to `Connected`. If none exists, it discovers the table's primary
field and creates a record labeled `Codex connection test` with status
`Connected`. It then re-reads the table and verifies the resulting record.

The optional target variables shown in `.env.example` may be omitted. If
provided, each must exactly match the documented Wiki node, table, and view;
the connector refuses any other target.

## Tests

The tests use an in-memory mock transport and make no Feishu requests:

```bash
cd feishu
python3 -m unittest -v test_connector.py
```

Authentication, Wiki resolution, table permission, and record-operation errors
are reported as distinct failures. Error messages include only safe operation
and numeric status/code details, not API response bodies.

## Required Feishu-side configuration

The `WML AI Operations` app must be enabled for the tenant, have access to the
documented Wiki/Bitable, and have Wiki plus Bitable read permissions. The
`--write-test` command additionally requires Bitable record-edit permission.
The target table must contain a `Status` field that accepts `Pending` and
`Connected`. These settings cannot be inferred or changed by this connector.

## Read-only workspace inventory

The inventory CLI reuses the connector authentication and secret-safe GET
transport. It recursively discovers accessible Wiki spaces/nodes and Drive
folders/files, inventories Bitable tables discovered through those surfaces,
and continues when an individual scope is inaccessible.
If the application cannot enumerate all Wiki spaces, discovery automatically
falls back to the designated Wiki node already configured and verified by the
Issue #1 connector; this is recorded as partial coverage rather than presented
as a complete workspace inventory.

```bash
python3 feishu/inventory.py
```

It writes a versioned machine-readable index to

- `feishu/inventory-output/inventory.json`
- `feishu/inventory-output/inventory-report.md`

The generated directory is ignored by Git. Output includes resource metadata
and retrieval identifiers but never credentials, access tokens, authorization
headers, document bodies, or Bitable record contents. Classification values are
metadata-based candidates with confidence/status, not an approved taxonomy.

The app needs the relevant read scopes and document access for Wiki node lists,
Drive folder listings, and Bitable table metadata. Feishu may expose only the
resources explicitly shared with a tenant application; inaccessible discovery
scopes are recorded as partial results rather than terminating the inventory.

Run all tests from the `feishu` directory:

```bash
python3 -m unittest -v
```

### Live read-only validation

The 2026-08-11 validation authenticated successfully and generated both output
formats without modifying Feishu. It discovered two accessible resources (one
Bitable/Base and one table) through the configured Wiki-node fallback. Global
Wiki-space enumeration returned HTTP 400 and was recorded as partial coverage;
the Drive root returned no accessible resources for the tenant application.
Broader inventory coverage therefore requires Feishu to grant the application
the relevant Wiki-space listing scope/data range and share additional Drive
folders or resources with the application.

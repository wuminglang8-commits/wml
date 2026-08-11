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
transport. It uses a controlled Business Knowledge Roots model because a tenant
application's Wiki/Drive roots are not a complete enterprise-wide workspace
index. It never treats an empty app Drive root as complete coverage and does
not perform global search or user OAuth.

Copy the committed template to the ignored local configuration file, then
replace the examples with the roots the application is allowed to read:

```bash
cp feishu/knowledge-roots.example.json feishu/knowledge-roots.json
```

Supported root types are:

- `wiki_space`: a Wiki space ID; scans all nodes below the space root.
- `wiki_node`: a Wiki node token; resolves and scans only that subtree.
- `drive_folder`: a shared Drive folder token; scans all nested files/folders.
- `bitable`: a Bitable app token; inventories the Base and its tables.

Root identifiers are retrieval metadata rather than credentials, but the live
configuration remains ignored to avoid publishing internal workspace layout.
Share each configured Wiki space/node or Drive folder with the tenant app and
grant its read-only scopes. A configured Base must also be readable by the app.
Do not add both a parent root and every child unless overlapping coverage is
intentional.

```bash
python3 feishu/inventory.py --roots-file feishu/knowledge-roots.json
```

It writes a versioned machine-readable index to

- `feishu/inventory-output/inventory.json`
- `feishu/inventory-output/inventory-report.md`

The generated directory is ignored by Git. Output includes resource metadata
and retrieval identifiers but never credentials, access tokens, authorization
headers, document bodies, or Bitable record contents. Classification values are
metadata-based candidates with confidence/status, not an approved taxonomy.

The report distinguishes discovered roots, inaccessible APIs, permission
denials, empty roots, unsupported global discovery, and partial coverage.
Failures remain isolated to their root so other configured roots continue.
Wiki node pagination uses Feishu's maximum supported page size of 50; Drive
folder pagination uses 200 and Bitable table pagination uses 100.

Run all tests from the `feishu` directory:

```bash
python3 -m unittest -v
```

### Previous live read-only validation

The 2026-08-11 validation authenticated successfully and generated both output
formats without modifying Feishu. It discovered two accessible resources (one
Bitable/Base and one table) through the configured Wiki-node fallback. Global
Wiki-space enumeration returned HTTP 400 and was recorded as partial coverage;
the Drive root returned no accessible resources for the tenant application.
The result demonstrated why global enumeration is insufficient. The next live
validation must use the controlled Knowledge Roots manifest described above.

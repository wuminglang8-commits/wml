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

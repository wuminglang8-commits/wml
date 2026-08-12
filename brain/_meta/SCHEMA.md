# Company Brain Schema

## Recommended frontmatter

```yaml
type: project | entity | decision | memory | system | source
status: active | paused | archived | draft
project:
entities: []
departments: []
topics: []
source: chatgpt | feishu | github | drive | manual
updated: YYYY-MM-DD
confidence: high | medium | low
```

## Linking model

A note may belong to multiple dimensions simultaneously. Do not force every resource into one folder-only category.

Primary dimensions:
- project
- department
- business line
- entity/partner
- document type
- time/status

Use wiki links to connect related notes. Examples:
- `[[02_PROJECTS/PROJECT_INDEX]]`
- `[[04_MEMORY/CHAT_MEMORY_SEED]]`

## Naming

Prefer durable human-readable names. Avoid unstable numeric prefixes except navigation/MOC notes. Do not encode secrets or external access tokens in filenames or frontmatter.

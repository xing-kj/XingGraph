# Data-source connectors

Connectors pull data from external sources (Gmail, Slack, Notion, Google Drive,
Confluence, …) into xinggraph memory. They are distributed as **community packages**
under [xing-kj/xinggraph-community](https://github.com/xing-kj/xinggraph-community)
(`xinggraph-community-connector-<source>`), so core stays free of per-source SDKs.

Every connector is built on xinggraph's **DLT ingestion subsystem**, so they all share
the same guarantees instead of each reinventing ingestion:

- **One call to ingest** — hand the connector's `dlt` source to `xinggraph.remember(...)`.
- **Incremental re-sync** — `write_disposition="merge"` upserts by primary key
  (or `replace` for full-snapshot sources); re-running only pulls the delta.
- **Forget-on-source-deletion** — records removed upstream are deleted from the
  graph + vector + relational stores via the shared `orphan_cleanup` path.
- **Prose ingested as documents** — connectors opt into the document path
  (`dlt_utils.DOCUMENT_SOURCE_ATTR`) so page/message text flows through normal
  cognify (LLM entity extraction), not the relational schema path.

## Available connectors

Install from PyPI; you do **not** need to clone the community monorepo to use them.

| Source | Package |
|---|---|
| Gmail | `xinggraph-community-connector-gmail` |
| Slack (export) | `xinggraph-community-connector-slack` |
| Confluence | `xinggraph-community-connector-confluence` |
| Notion | `xinggraph-community-connector-notion` |
| Google Drive | `xinggraph-community-connector-google-drive` |

## Quickstart (Gmail)

```bash
pip install xinggraph-community-connector-gmail
```

```python
import xinggraph
from xinggraph_community_connector_gmail import gmail_source

await xinggraph.remember(
    gmail_source(label_ids=["INBOX"], credentials_path="credentials.json"),
    dataset_name="gmail_inbox",
    primary_key="id",
    write_disposition="merge",
    max_rows_per_table=0,   # 0 = no read cap, so forget-on-delete sees the whole inbox
)

answer = await xinggraph.search(
    query_text="What did my manager ask me to do this week?",
    datasets=["gmail_inbox"],
)
```

See each package's `README.md` + `examples/` in the community repo for setup,
incremental re-sync, and privacy / opt-in notes.

## Writing a new connector

Publish a `xinggraph-community-connector-<source>` package (see the ones above as
templates). The connector exposes a factory returning a `dlt` source with a
`primary_key`, a `write_disposition`, and a `hard_delete` marker column for
deletions; for prose sources set `DOCUMENT_SOURCE_ATTR` so rows are ingested as
documents. Keep the third-party SDK a lazy import, and ship mocked-SaaS +
mocked-LLM tests (no live credentials in CI).

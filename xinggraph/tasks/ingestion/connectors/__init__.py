"""SaaS data-source connectors for xinggraph.

Connectors that pull an external source (Gmail, Slack, Notion, Google Drive,
Confluence, …) into xinggraph memory are distributed as **separate community
packages** under https://github.com/xing-kj/xinggraph-community
(``xinggraph-community-connector-<source>``), so core stays free of per-source SDKs.

Each connector is a plain ``dlt`` source you hand to ``xinggraph.remember(...)``. It
reuses core's DLT ingestion path (``resolve_dlt_sources`` -> ``ingest_dlt_source``
-> ``orphan_cleanup``) for incremental re-sync and forget-on-source-deletion, and
opts into the document ingestion path via ``dlt_utils.DOCUMENT_SOURCE_ATTR``. No
connector is bundled in core::

    pip install xinggraph-community-connector-gmail
    from xinggraph_community_connector_gmail import gmail_source

    await xinggraph.remember(gmail_source(...), dataset_name="gmail_inbox")
"""

__all__: list[str] = []

"""Public migration API: move memory into and out of XingGraph.

Importing from other memory systems (pass any source to ``xinggraph.remember``)::

    from xinggraph.migration import Mem0Source, ZepSource, LettaSource

    await xinggraph.remember(Mem0Source("mem0_export.json"))
    await xinggraph.remember(ZepSource("graphiti_dump.json", mode="hybrid"))

Exporting (``xinggraph.export``)::

    snapshot = await xinggraph.export("main_dataset")     # GraphSnapshot: typed
    alice = snapshot.find(name="Alice")[0]             # real DataPoint objects
    result = await xinggraph.export("main_dataset", format="graphml")

Restoring / XingGraph-to-XingGraph migration::

    await xinggraph.export("main_dataset", format="cogx", destination="backup_cogx")
    await xinggraph.remember(COGXArchiveSource("backup_cogx"))
"""

from xinggraph.modules.migration import (
    COGX_VERSION,
    COGXArchiveSource,
    COGXDocument,
    COGXEntity,
    COGXEpisode,
    COGXFact,
    COGXManifest,
    COGXMemory,
    COGXMemoryBlock,
    COGXRawNode,
    COGXRecord,
    COGXScope,
    COGXTurn,
    EXPORT_FORMATS,
    ExportResult,
    GraphEdge,
    GraphSnapshot,
    GraphitiSource,
    IMPORT_MODES,
    LettaSource,
    Mem0Source,
    MemorySource,
    ZepSource,
    build_snapshot,
    datapoint_registry,
    export_dataset,
    read_archive,
    read_manifest,
    rehydrate_node,
)

__all__ = [
    "COGX_VERSION",
    "COGXArchiveSource",
    "COGXDocument",
    "COGXEntity",
    "COGXEpisode",
    "COGXFact",
    "COGXManifest",
    "COGXMemory",
    "COGXMemoryBlock",
    "COGXRawNode",
    "COGXRecord",
    "COGXScope",
    "COGXTurn",
    "EXPORT_FORMATS",
    "ExportResult",
    "GraphEdge",
    "GraphSnapshot",
    "GraphitiSource",
    "IMPORT_MODES",
    "LettaSource",
    "Mem0Source",
    "MemorySource",
    "ZepSource",
    "build_snapshot",
    "datapoint_registry",
    "export_dataset",
    "read_archive",
    "read_manifest",
    "rehydrate_node",
]

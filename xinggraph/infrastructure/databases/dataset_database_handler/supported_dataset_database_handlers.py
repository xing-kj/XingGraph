from xinggraph.infrastructure.databases.graph.neo4j_driver.Neo4jAuraDevDatasetDatabaseHandler import (
    Neo4jAuraDevDatasetDatabaseHandler,
)
from xinggraph.infrastructure.databases.graph.neo4j_driver.Neo4jDatasetDatabaseHandler import (
    Neo4jDatasetDatabaseHandler,
)
from xinggraph.infrastructure.databases.vector.lancedb.LanceDBDatasetDatabaseHandler import (
    LanceDBDatasetDatabaseHandler,
)
from xinggraph.infrastructure.databases.vector.qdrant.QdrantDatasetDatabaseHandler import (
    QdrantDatasetDatabaseHandler,
)
from xinggraph.infrastructure.databases.graph.ladybug.LadybugDatasetDatabaseHandler import (
    LadybugDatasetDatabaseHandler,
)
from xinggraph.infrastructure.databases.vector.pgvector.PGVectorDatasetDatabaseHandler import (
    PGVectorDatasetDatabaseHandler,
)
from xinggraph.infrastructure.databases.graph.postgres.PostgresGraphDatasetDatabaseHandler import (
    PostgresGraphDatasetDatabaseHandler,
)

supported_dataset_database_handlers = {
    "neo4j_aura_dev": {
        "handler_instance": Neo4jAuraDevDatasetDatabaseHandler,
        "handler_provider": "neo4j",
    },
    "neo4j": {
        "handler_instance": Neo4jDatasetDatabaseHandler,
        "handler_provider": "neo4j",
    },
    "lancedb": {"handler_instance": LanceDBDatasetDatabaseHandler, "handler_provider": "lancedb"},
    "qdrant": {"handler_instance": QdrantDatasetDatabaseHandler, "handler_provider": "qdrant"},
    "pgvector": {
        "handler_instance": PGVectorDatasetDatabaseHandler,
        "handler_provider": "pgvector",
    },
    "postgres_graph": {
        "handler_instance": PostgresGraphDatasetDatabaseHandler,
        "handler_provider": "postgres",
    },
    "ladybug": {
        "handler_instance": LadybugDatasetDatabaseHandler,
        "handler_provider": "ladybug",
    },
    "kuzu": {"handler_instance": LadybugDatasetDatabaseHandler, "handler_provider": "kuzu"},
}

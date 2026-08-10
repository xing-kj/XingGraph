from unittest.mock import MagicMock

import pytest

from xinggraph.infrastructure.engine.models.Edge import Edge
from xinggraph.modules.graph.utils.expand_with_nodes_and_edges import expand_with_nodes_and_edges
from xinggraph.shared.data_models import KnowledgeGraph, Node, Edge as KGEdge
from xinggraph.modules.ontology.models import AttachedOntologyNode


def _mock_resolver():
    """Mock resolver that returns no ontology match (entities are uncertain).

    Reports an empty ObjectProperty whitelist, so no non-is_a LLM edges are
    persisted.
    """
    resolver = MagicMock()
    resolver.get_subgraph.return_value = ([], [], None)
    resolver.get_object_properties.return_value = set()
    return resolver


def _mock_resolver_with_whitelist(properties):
    """Mock resolver that returns no ontology match but a fixed whitelist."""
    resolver = _mock_resolver()
    resolver.get_object_properties.return_value = set(properties)
    return resolver


def _mock_resolver_with_match():
    """Mock resolver that returns an ontology match for common entity names.

    This simulates entities that are found in the ontology, so they get
    ontology_valid=True and LLM-extracted edges are kept.
    """
    resolver = MagicMock()

    _known_individuals = {
        "alice": AttachedOntologyNode(uri="http://example.org/ontology#Alice", category="individuals"),
        "bob": AttachedOntologyNode(uri="http://example.org/ontology#Bob", category="individuals"),
        "acme": AttachedOntologyNode(uri="http://example.org/ontology#Acme", category="individuals"),
    }
    person_class = AttachedOntologyNode(uri="http://example.org/ontology#Person", category="classes")
    company_class = AttachedOntologyNode(uri="http://example.org/ontology#Company", category="classes")

    def _get_subgraph(node_name, node_type="individuals", directed=True):
        normalized = node_name.lower().replace(" ", "_").strip()
        if node_type == "individuals":
            ind = _known_individuals.get(normalized)
            if ind:
                cls = person_class if normalized in ("alice", "bob") else company_class
                return ([ind, cls], [(normalized, "is_a", cls.name)], ind)
            return ([], [], None)
        else:
            return ([person_class], [("person", "is_a", "thing")], person_class)

    resolver.get_subgraph.side_effect = _get_subgraph
    resolver.get_class_hierarchy.return_value = {"person": []}
    resolver.get_all_ancestors.return_value = []
    resolver.get_type_chain.side_effect = lambda name: [name.lower().replace(" ", "_"), "person"]
    resolver.is_subclass_of.return_value = False
    resolver.get_property_domain_range.return_value = {"domain": [], "range": []}
    resolver.get_object_properties.return_value = {"knows", "works_at", "is_product"}
    resolver.graph = None
    return resolver


def _make_chunk(importance_weight=0.5):
    from unittest.mock import MagicMock as MM

    chunk = MM()
    chunk.contains = None
    chunk.belongs_to_set = []
    chunk.importance_weight = importance_weight
    return chunk


def _make_graph(nodes, edges):
    return KnowledgeGraph(nodes=nodes, edges=edges)


def test_chunk_contains_populated():
    chunk = _make_chunk()
    graph = _make_graph(
        [Node(id="n1", name="Alice", type="Person", description="A person")],
        [],
    )
    chunks, entity_nodes = expand_with_nodes_and_edges([chunk], [graph], _mock_resolver())

    assert chunk.contains is not None
    assert len(chunk.contains) == 1
    _, entity = chunk.contains[0]
    assert entity.name == "alice"


def test_entity_relations_populated_from_graph_edges():
    chunk = _make_chunk()
    graph = _make_graph(
        [
            Node(id="n1", name="Alice", type="Person", description="desc"),
            Node(id="n2", name="Bob", type="Person", description="desc"),
        ],
        [KGEdge(source_node_id="n1", target_node_id="n2", relationship_name="knows")],
    )
    _, entity_nodes = expand_with_nodes_and_edges([chunk], [graph], _mock_resolver_with_match())

    alice = next(e for e in entity_nodes if e.name == "alice")
    # Alice should have at least the LLM "knows" edge and possibly ontology "is_a" edges
    knows_edges = [
        (edge_obj, target)
        for edge_obj, target in alice.relations
        if edge_obj.relationship_type == "knows"
    ]
    assert len(knows_edges) == 1
    edge_obj, target = knows_edges[0]
    assert target.name == "bob"
    assert edge_obj.edge_text is None


def test_chunk_contains_edge_text_uses_per_chunk_description():
    chunk1, chunk2 = _make_chunk(), _make_chunk()
    graph1 = _make_graph(
        [Node(id="n1", name="Alice", type="Person", description="Alice founded Acme.")],
        [],
    )
    graph2 = _make_graph(
        [Node(id="n1", name="Alice", type="Person", description="Alice lives in Paris.")],
        [],
    )

    expand_with_nodes_and_edges([chunk1, chunk2], [graph1, graph2], _mock_resolver())

    first_edge, first_entity = chunk1.contains[0]
    second_edge, second_entity = chunk2.contains[0]

    assert first_entity is second_entity
    assert first_edge.edge_text == "Document chunk mentions alice: Alice founded Acme."
    assert second_edge.edge_text == "Document chunk mentions alice: Alice lives in Paris."


def test_blank_chunk_description_leaves_edge_text_none_before_storage():
    chunk = _make_chunk()
    graph = _make_graph(
        [Node(id="n1", name="Alice", type="Person", description="   ")],
        [],
    )

    expand_with_nodes_and_edges([chunk], [graph], _mock_resolver())

    edge_obj, _ = chunk.contains[0]
    assert edge_obj.edge_text is None


def test_entity_relation_preserves_llm_edge_description():
    chunk = _make_chunk()
    graph = _make_graph(
        [
            Node(id="n1", name="Alice", type="Person", description="desc"),
            Node(id="n2", name="Acme", type="Company", description="desc"),
        ],
        [
            KGEdge(
                source_node_id="n1",
                target_node_id="n2",
                relationship_name="works_at",
                description="Alice works at Acme.",
            )
        ],
    )

    _, entity_nodes = expand_with_nodes_and_edges([chunk], [graph], _mock_resolver_with_match())

    alice = next(e for e in entity_nodes if e.name == "alice")
    works_at_edges = [
        (edge_obj, target)
        for edge_obj, target in alice.relations
        if edge_obj.relationship_type == "works_at"
    ]
    assert len(works_at_edges) == 1
    edge_obj, target = works_at_edges[0]
    assert target.name == "acme"
    assert edge_obj.edge_text == "Alice works at Acme."


def test_edge_model_does_not_default_edge_text_from_relationship_type():
    assert Edge(relationship_type="contains").edge_text is None


def test_returns_chunks_and_entity_nodes():
    chunk = _make_chunk()
    graph = _make_graph(
        [Node(id="n1", name="Thing", type="Object", description="a thing")],
        [],
    )
    result = expand_with_nodes_and_edges([chunk], [graph], _mock_resolver())

    assert isinstance(result, tuple) and len(result) == 2
    returned_chunks, entity_nodes = result
    assert returned_chunks is not None
    assert isinstance(entity_nodes, list)


def test_empty_graph_skipped():
    chunk = _make_chunk()
    chunks, entity_nodes = expand_with_nodes_and_edges([chunk], [None], _mock_resolver())

    assert chunk.contains is None
    assert entity_nodes == []


def test_entity_deduplication_across_chunks():
    chunk1, chunk2 = _make_chunk(), _make_chunk()
    node = Node(id="n1", name="Alice", type="Person", description="desc")
    graph1 = _make_graph([node], [])
    graph2 = _make_graph([node], [])

    _, entity_nodes = expand_with_nodes_and_edges(
        [chunk1, chunk2], [graph1, graph2], _mock_resolver()
    )

    alice_nodes = [e for e in entity_nodes if e.name == "alice"]
    assert len(alice_nodes) == 1


def test_importance_weight_propagates_to_created_nodes():
    chunk = _make_chunk()
    chunk.importance_weight = 0.9
    graph = _make_graph(
        [Node(id="n1", name="Alice", type="Person", description="A person")],
        [],
    )

    _, entity_nodes = expand_with_nodes_and_edges([chunk], [graph], _mock_resolver())

    alice = next(node for node in entity_nodes if node.name == "alice")
    person = next(node for node in entity_nodes if node.name == "person")
    _, contained_entity = chunk.contains[0]

    assert alice.importance_weight == 0.9
    assert person.importance_weight == 0.9
    assert contained_entity.importance_weight == 0.9


def test_default_importance_weight_propagates_to_created_nodes():
    chunk = _make_chunk()
    graph = _make_graph(
        [Node(id="n1", name="Alice", type="Person", description="A person")],
        [],
    )

    _, entity_nodes = expand_with_nodes_and_edges([chunk], [graph], _mock_resolver())

    alice = next(node for node in entity_nodes if node.name == "alice")
    person = next(node for node in entity_nodes if node.name == "person")
    _, contained_entity = chunk.contains[0]

    assert alice.importance_weight == 0.5
    assert person.importance_weight == 0.5
    assert contained_entity.importance_weight == 0.5


def test_unknown_entity_has_no_semantic_edges():
    """Entities with no ontology match should not get non-whitelisted LLM edges."""
    chunk = _make_chunk()
    graph = _make_graph(
        [
            Node(id="n1", name="Alice", type="Person", description="desc"),
            Node(id="n2", name="Bob", type="Person", description="desc"),
        ],
        [KGEdge(source_node_id="n1", target_node_id="n2", relationship_name="knows")],
    )
    # _mock_resolver returns no match → both entities are uncertain, and the
    # whitelist is empty, so "knows" is not a declared ObjectProperty.
    _, entity_nodes = expand_with_nodes_and_edges([chunk], [graph], _mock_resolver())

    alice = next(e for e in entity_nodes if e.name == "alice")
    assert alice.ontology_valid is False
    assert len(alice.relations) == 0  # no semantic edges for uncertain entities
    # is_a is always allowed, so the type link is preserved
    assert alice.is_a is not None and alice.is_a.name == "person"


def test_whitelisted_is_product_edge_kept_for_uncertain_entities():
    """is_product edges are persisted even when the endpoints have no ontology
    match, as long as is_product is a declared ObjectProperty."""
    chunk = _make_chunk()
    graph = _make_graph(
        [
            Node(id="n1", name="Medical low-temperature preservation box", type="Product", description="desc"),
            Node(id="n2", name="DW-86L100STL", type="PRODUCT_MODEL", description="desc"),
        ],
        [
            KGEdge(
                source_node_id="n1",
                target_node_id="n2",
                relationship_name="is_product",
                description="The medical low-temperature preservation box family includes the DW-86L100STL model.",
            )
        ],
    )
    resolver = _mock_resolver_with_whitelist({"is_product"})
    _, entity_nodes = expand_with_nodes_and_edges([chunk], [graph], resolver)

    product = next(e for e in entity_nodes if e.name == "medical low-temperature preservation box")
    assert product.ontology_valid is False
    is_product_edges = [
        (edge_obj, target)
        for edge_obj, target in product.relations
        if edge_obj.relationship_type == "is_product"
    ]
    assert len(is_product_edges) == 1
    edge_obj, target = is_product_edges[0]
    assert target.name == "dw-86l100stl"
    assert edge_obj.edge_text == "The medical low-temperature preservation box family includes the DW-86L100STL model."


def test_non_whitelisted_edge_dropped_even_with_match():
    """LLM edges outside the whitelist are dropped even when the entities have
    an ontology match — the whitelist is the gate, not ontology_valid."""
    chunk = _make_chunk()
    graph = _make_graph(
        [
            Node(id="n1", name="Alice", type="Person", description="desc"),
            Node(id="n2", name="Bob", type="Person", description="desc"),
        ],
        [KGEdge(source_node_id="n1", target_node_id="n2", relationship_name="knows")],
    )
    # Only is_product is whitelisted; "knows" must be dropped.
    resolver = _mock_resolver_with_match()
    resolver.get_object_properties.return_value = {"is_product"}
    _, entity_nodes = expand_with_nodes_and_edges([chunk], [graph], resolver)

    alice = next(e for e in entity_nodes if e.name == "alice")
    knows_edges = [
        (edge_obj, target)
        for edge_obj, target in alice.relations
        if edge_obj.relationship_type == "knows"
    ]
    assert len(knows_edges) == 0


def test_reject_unknown_entities_drops_entity():
    """With reject_unknown_entities=True, unknown entity nodes are not created,
    but type nodes (EntityType) are still created since they may be shared."""
    chunk = _make_chunk()
    graph = _make_graph(
        [
            Node(id="n1", name="Alice", type="Person", description="desc"),
            Node(id="n2", name="Bob", type="Person", description="desc"),
        ],
        [KGEdge(source_node_id="n1", target_node_id="n2", relationship_name="knows")],
    )
    chunks, entity_nodes = expand_with_nodes_and_edges(
        [chunk], [graph], _mock_resolver(), reject_unknown_entities=True
    )

    # No Entity nodes should be returned (only EntityType nodes may remain)
    entity_only = [n for n in entity_nodes if hasattr(n, "is_a")]
    assert len(entity_only) == 0
    # No contains edges for rejected entities
    assert chunk.contains is None or len(chunk.contains) == 0

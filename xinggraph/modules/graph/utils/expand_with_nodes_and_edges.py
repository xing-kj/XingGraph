from typing import Optional
import logging

from rdflib import RDF

from xinggraph.infrastructure.engine.models.Edge import Edge
from xinggraph.modules.chunking.models import DocumentChunk
from xinggraph.modules.engine.models import Entity, EntityType
from xinggraph.modules.engine.utils import (
    generate_edge_name,
    generate_node_name,
)
from xinggraph.modules.ontology.base_ontology_resolver import BaseOntologyResolver
from xinggraph.modules.ontology.ontology_env_config import get_ontology_env_config
from xinggraph.shared.data_models import KnowledgeGraph, ChunkWiki
from xinggraph.modules.ontology.rdf_xml.RDFLibOntologyResolver import RDFLibOntologyResolver
from xinggraph.modules.ontology.get_default_ontology_resolver import (
    get_default_ontology_resolver,
    get_ontology_resolver_from_env,
)

logger = logging.getLogger("OntologyExpansion")


def _create_node_key(node_id: str, category: str) -> str:
    """Create a standardized node key"""
    return f"{node_id}_{category}"


def _create_edge_key(source_id: str, target_id: str, relationship_name: str) -> str:
    """Create a standardized edge key"""
    return f"{source_id}_{target_id}_{relationship_name}"


def _strip_nonblank_text(value: str | None) -> str | None:
    if value is None:
        return None

    stripped_value = value.strip()
    return stripped_value or None


def _process_ontology_nodes(
    ontology_nodes: list,
    data_chunk: DocumentChunk,
    added_nodes_map: dict,
    added_ontology_nodes_map: dict,
) -> None:
    """Process and store ontology nodes"""
    for ontology_node in ontology_nodes:
        ont_node_id = (
            EntityType.id_for(ontology_node.name)
            if ontology_node.category == "classes"
            else Entity.id_for(ontology_node.name)
        )
        ont_node_name = generate_node_name(ontology_node.name)
        # Preserve the source ontology IRI on the stored node (Phase 0). The
        # AttachedOntologyNode carries the rdflib URIRef; stringify it so the
        # identifier survives persistence into the property graph.
        ont_node_uri = str(ontology_node.uri) if ontology_node.uri is not None else None

        if ontology_node.category == "classes":
            ont_node_key = _create_node_key(ont_node_id, "type")
            if ont_node_key not in added_nodes_map and ont_node_key not in added_ontology_nodes_map:
                added_ontology_nodes_map[ont_node_key] = EntityType(
                    id=ont_node_id,
                    name=ont_node_name,
                    description=ont_node_name,
                    ontology_valid=True,
                    ontology_uri=ont_node_uri,
                    importance_weight=data_chunk.importance_weight,
                )

        elif ontology_node.category == "individuals":
            ont_node_key = _create_node_key(ont_node_id, "entity")
            if ont_node_key not in added_nodes_map and ont_node_key not in added_ontology_nodes_map:
                added_ontology_nodes_map[ont_node_key] = Entity(
                    id=ont_node_id,
                    name=ont_node_name,
                    description=ont_node_name,
                    ontology_valid=True,
                    ontology_uri=ont_node_uri,
                    belongs_to_set=data_chunk.belongs_to_set,
                    importance_weight=data_chunk.importance_weight,
                )


def _process_ontology_edges(
    ontology_nodes: list,
    ontology_edges: list,
    existing_edges_map: dict,
    ontology_relationships: list,
    ontology_resolver: "RDFLibOntologyResolver" = None,
) -> None:
    """Process ontology edges and add them if new.

    If ontology_resolver is provided, validates domain/range constraints on
    ObjectProperty edges before creating them.
    """
    node_category = {node.name: node.category for node in ontology_nodes}

    # Build reverse lookup: class_key -> set of individual keys that are of that class
    # Used for domain/range validation (checking if individual belongs to a class)
    individual_class_map: dict = {}
    if ontology_resolver is not None and ontology_resolver.graph is not None:
        for ind_key, ind_uri in ontology_resolver.lookup.get("individuals", {}).items():
            for parent_uri in ontology_resolver.graph.objects(ind_uri, RDF.type):
                parent_key = ontology_resolver._uri_to_key(parent_uri)
                if parent_key not in individual_class_map:
                    individual_class_map[parent_key] = set()
                individual_class_map[parent_key].add(ind_key)

    for source, relation, target in ontology_edges:
        source_cls = EntityType if node_category.get(source) == "classes" else Entity
        target_cls = EntityType if node_category.get(target) == "classes" else Entity
        source_node_id = source_cls.id_for(source)
        target_node_id = target_cls.id_for(target)
        relationship_name = generate_edge_name(relation)
        edge_key = _create_edge_key(source_node_id, target_node_id, relationship_name)

        # Domain/range validation for ObjectProperty edges
        if ontology_resolver is not None and relationship_name != "is_a":
            dr = ontology_resolver.get_property_domain_range(relation)
            if dr.get("domain") or dr.get("range"):
                source_category = node_category.get(source, "unknown")
                target_category = node_category.get(target, "unknown")

                # Check domain: source must be an instance of (or be) a domain class
                if dr.get("domain"):
                    domain_ok = False
                    if source_category == "classes":
                        # Source is a class; check if it matches or is subclass of any domain class
                        for domain_class in dr["domain"]:
                            if source == domain_class or ontology_resolver.is_subclass_of(
                                source, domain_class
                            ):
                                domain_ok = True
                                break
                    else:
                        # Source is an individual; check its type chain
                        source_ancestors = set(ontology_resolver.get_all_ancestors(source))
                        source_ancestors.add(source)
                        for domain_class in dr["domain"]:
                            if domain_class in source_ancestors:
                                domain_ok = True
                                break
                            # Also check if the individual's direct type matches
                            for ind_key in individual_class_map.get(domain_class, set()):
                                if ind_key == source:
                                    domain_ok = True
                                    break
                            if domain_ok:
                                break

                    if not domain_ok:
                        logger.warning(
                            "Domain constraint violated: '%s' is not in domain '%s' of property '%s'. Skipping edge.",
                            source,
                            dr["domain"],
                            relation,
                        )
                        continue

                # Check range: target must be an instance of (or be) a range class
                if dr.get("range"):
                    range_ok = False
                    if target_category == "classes":
                        for range_class in dr["range"]:
                            if target == range_class or ontology_resolver.is_subclass_of(
                                target, range_class
                            ):
                                range_ok = True
                                break
                    else:
                        target_ancestors = set(ontology_resolver.get_all_ancestors(target))
                        target_ancestors.add(target)
                        for range_class in dr["range"]:
                            if range_class in target_ancestors:
                                range_ok = True
                                break
                            for ind_key in individual_class_map.get(range_class, set()):
                                if ind_key == target:
                                    range_ok = True
                                    break
                            if range_ok:
                                break

                    if not range_ok:
                        logger.warning(
                            "Range constraint violated: '%s' is not in range '%s' of property '%s'. Skipping edge.",
                            target,
                            dr["range"],
                            relation,
                        )
                        continue

        if edge_key not in existing_edges_map:
            ontology_relationships.append(
                (
                    source_node_id,
                    target_node_id,
                    relationship_name,
                    {
                        "relationship_name": relationship_name,
                        "source_node_id": source_node_id,
                        "target_node_id": target_node_id,
                        "ontology_valid": True,
                    },
                )
            )
            existing_edges_map[edge_key] = True


def _create_type_node(
    node_type: str,
    ontology_resolver: RDFLibOntologyResolver,
    added_nodes_map: dict,
    added_ontology_nodes_map: dict,
    name_mapping: dict,
    key_mapping: dict,
    data_chunk: DocumentChunk,
    existing_edges_map: dict,
    ontology_relationships: list,
) -> EntityType:
    """Create or retrieve a type node with ontology validation"""
    node_id = EntityType.id_for(node_type)
    node_name = generate_node_name(node_type)
    type_node_key = _create_node_key(node_id, "type")

    if type_node_key in added_nodes_map or type_node_key in key_mapping:
        return added_nodes_map.get(type_node_key) or added_nodes_map.get(
            key_mapping.get(type_node_key)
        )

    # Get ontology validation
    ontology_nodes, ontology_edges, closest_class = ontology_resolver.get_subgraph(
        node_name=node_name, node_type="classes"
    )

    ontology_validated = bool(closest_class)
    ontology_uri = None

    if ontology_validated:
        old_key = type_node_key
        node_id = EntityType.id_for(closest_class.name)
        type_node_key = _create_node_key(node_id, "type")
        new_node_name = generate_node_name(closest_class.name)
        ontology_uri = str(closest_class.uri) if closest_class.uri is not None else None

        name_mapping[node_name] = closest_class.name
        key_mapping[old_key] = type_node_key
        node_name = new_node_name

    type_node = EntityType(
        id=node_id,
        name=node_name,
        type=node_name,
        description=node_name,
        ontology_valid=ontology_validated,
        ontology_uri=ontology_uri,
        importance_weight=data_chunk.importance_weight,
    )

    added_nodes_map[type_node_key] = type_node

    # Process ontology nodes and edges
    _process_ontology_nodes(ontology_nodes, data_chunk, added_nodes_map, added_ontology_nodes_map)
    _process_ontology_edges(
        ontology_nodes, ontology_edges, existing_edges_map, ontology_relationships,
        ontology_resolver=ontology_resolver,
    )

    return type_node


def _create_entity_node(
    node_id: str,
    node_name: str,
    node_description: str,
    type_node: EntityType,
    ontology_resolver: RDFLibOntologyResolver,
    added_nodes_map: dict,
    added_ontology_nodes_map: dict,
    name_mapping: dict,
    key_mapping: dict,
    data_chunk: DocumentChunk,
    existing_edges_map: dict,
    ontology_relationships: list,
) -> Entity:
    """Create or retrieve an entity node with ontology validation"""
    generated_node_id = Entity.id_for(node_id)
    generated_node_name = generate_node_name(node_name)
    entity_node_key = _create_node_key(generated_node_id, "entity")

    if entity_node_key in added_nodes_map or entity_node_key in key_mapping:
        return added_nodes_map.get(entity_node_key) or added_nodes_map.get(
            key_mapping.get(entity_node_key)
        )

    # Get ontology validation
    ontology_nodes, ontology_edges, start_ent_ont = ontology_resolver.get_subgraph(
        node_name=generated_node_name, node_type="individuals"
    )

    ontology_validated = bool(start_ent_ont)
    ontology_uri = None

    if ontology_validated:
        old_key = entity_node_key
        generated_node_id = Entity.id_for(start_ent_ont.name)
        entity_node_key = _create_node_key(generated_node_id, "entity")
        new_node_name = generate_node_name(start_ent_ont.name)
        ontology_uri = str(start_ent_ont.uri) if start_ent_ont.uri is not None else None

        name_mapping[generated_node_name] = start_ent_ont.name
        key_mapping[old_key] = entity_node_key
        generated_node_name = new_node_name

    # Build ontology reasoning chain for Problem 6
    reasoning_chain = None
    if ontology_validated and ontology_resolver is not None:
        try:
            from xinggraph.modules.ontology.ontology_reasoning import (
                generate_ontology_reasoning_chain,
            )

            type_name = type_node.name if type_node else ""
            reasoning_chain = generate_ontology_reasoning_chain(
                generated_node_name, type_name, ontology_resolver
            )
        except (NotImplementedError, AttributeError):
            pass

    entity_node = Entity(
        id=generated_node_id,
        name=generated_node_name,
        is_a=type_node,
        description=node_description,
        ontology_valid=ontology_validated,
        ontology_uri=ontology_uri,
        ontology_reasoning_chain=reasoning_chain,
        belongs_to_set=data_chunk.belongs_to_set,
        # TODO add importance_weight calculation if an entity with that id already exits
        importance_weight=data_chunk.importance_weight,
    )

    added_nodes_map[entity_node_key] = entity_node

    # Process ontology nodes and edges
    _process_ontology_nodes(ontology_nodes, data_chunk, added_nodes_map, added_ontology_nodes_map)
    _process_ontology_edges(
        ontology_nodes, ontology_edges, existing_edges_map, ontology_relationships,
        ontology_resolver=ontology_resolver,
    )

    return entity_node


def _process_graph_nodes(
    data_chunk: DocumentChunk,
    graph: KnowledgeGraph,
    ontology_resolver: RDFLibOntologyResolver,
    added_nodes_map: dict,
    added_ontology_nodes_map: dict,
    name_mapping: dict,
    key_mapping: dict,
    existing_edges_map: dict,
    ontology_relationships: list,
    reject_unknown_entities: bool = False,
) -> None:
    """Process nodes in a knowledge graph.

    Args:
        reject_unknown_entities: If True, entities that don't match any ontology
            individual are silently dropped. If False (default), they are created
            as Entity nodes with ontology_valid=False but NO semantic edges
            (is_a / produces / develops etc.) are generated for them — only the
            "contains" edge from the document chunk is kept.
    """
    for node in graph.nodes:
        # Create type node
        type_node = _create_type_node(
            node.type,
            ontology_resolver,
            added_nodes_map,
            added_ontology_nodes_map,
            name_mapping,
            key_mapping,
            data_chunk,
            existing_edges_map,
            ontology_relationships,
        )

        # Create entity node
        entity_node = _create_entity_node(
            node.id,
            node.name,
            node.description,
            type_node,
            ontology_resolver,
            added_nodes_map,
            added_ontology_nodes_map,
            name_mapping,
            key_mapping,
            data_chunk,
            existing_edges_map,
            ontology_relationships,
        )

        # --- Unknown entity hard boundary ---
        if not entity_node.ontology_valid:
            if reject_unknown_entities:
                logger.info(
                    "Rejecting unknown entity '%s' (no ontology match). "
                    "Remove ontology_file_path or add this entity to the ontology to keep it.",
                    node.id,
                )
                # Remove the entity from both maps using the original key
                entity_key = _create_node_key(Entity.id_for(node.id), "entity")
                added_nodes_map.pop(entity_key, None)
                added_ontology_nodes_map.pop(entity_key, None)
                # Also try the name-based key (in case name_mapping remapped)
                name_key = _create_node_key(
                    Entity.id_for(generate_node_name(node.name)), "entity"
                )
                added_nodes_map.pop(name_key, None)
                added_ontology_nodes_map.pop(name_key, None)
                continue  # skip creating any node or edge for this entity
            else:
                # Uncertain entity (no ontology match): keep the entity and its
                # is_a type link — is_a is always allowed. Semantic ObjectProperty
                # edges are gated separately in _process_graph_edges by the
                # relationship whitelist (get_object_properties()).
                logger.info(
                    "Entity '%s' has no ontology match — created as uncertain "
                    "(ontology_valid=False).",
                    node.id,
                )

        if data_chunk.contains is None:
            data_chunk.contains = []

        entity_description = _strip_nonblank_text(node.description)
        edge_text = (
            f"Document chunk mentions {entity_node.name}: {entity_description}"
            if entity_description
            else None
        )

        data_chunk.contains.append(
            (
                Edge(
                    relationship_type="contains",
                    edge_text=edge_text,
                ),
                entity_node,
            )
        )


def _process_graph_edges(
    graph: KnowledgeGraph, name_mapping: dict, existing_edges_map: dict, relationships: list,
    added_nodes_map: dict = None, key_mapping: dict = None,
    ontology_resolver: BaseOntologyResolver = None,
) -> None:
    """Process edges in a knowledge graph.

    Edges are gated by a relationship whitelist: ``is_a`` is always allowed,
    and any other relationship is persisted only when its name is a declared
    ObjectProperty in the ontology (``get_object_properties()``). Edges whose
    source or target entity node was dropped (e.g. by reject_unknown_entities)
    are skipped to prevent dangling references.
    """
    object_properties = set()
    if ontology_resolver is not None:
        get_object_properties = getattr(ontology_resolver, "get_object_properties", None)
        if callable(get_object_properties):
            object_properties = set(get_object_properties())

    for edge in graph.edges:
        # Normalize before lookup so case differences don't cause misses
        source_id = name_mapping.get(generate_node_name(edge.source_node_id), edge.source_node_id)
        target_id = name_mapping.get(generate_node_name(edge.target_node_id), edge.target_node_id)

        source_node_id = Entity.id_for(source_id)
        target_node_id = Entity.id_for(target_id)
        relationship_name = generate_edge_name(edge.relationship_name)
        edge_key = _create_edge_key(source_node_id, target_node_id, relationship_name)
        edge_text = _strip_nonblank_text(edge.description)

        # Whitelist gate: is_a is always allowed; other relationships must be
        # declared ObjectProperties in the ontology (e.g. is_product).
        if relationship_name != "is_a" and relationship_name not in object_properties:
            logger.debug(
                "Skipping edge '%s' -> '%s' (%s): not a whitelisted ObjectProperty",
                source_id, target_id, relationship_name,
            )
            continue

        # Skip edges whose source or target node was dropped (reject_unknown_entities)
        if added_nodes_map is not None and key_mapping is not None:
            source_entity_key = key_mapping.get(
                f"{source_node_id}_entity", f"{source_node_id}_entity"
            )
            target_entity_key = key_mapping.get(
                f"{target_node_id}_entity", f"{target_node_id}_entity"
            )
            source_node = added_nodes_map.get(source_entity_key)
            target_node = added_nodes_map.get(target_entity_key)

            # Also check without key_mapping fallback
            if source_node is None:
                source_node = added_nodes_map.get(f"{source_node_id}_entity")
            if target_node is None:
                target_node = added_nodes_map.get(f"{target_node_id}_entity")

            if source_node is None:
                logger.debug(
                    "Skipping edge '%s' -> '%s': source entity node missing",
                    source_id, target_id,
                )
                continue
            if target_node is None:
                logger.debug(
                    "Skipping edge '%s' -> '%s': target entity node missing",
                    source_id, target_id,
                )
                continue

        if edge_key not in existing_edges_map:
            relationships.append(
                (
                    source_node_id,
                    target_node_id,
                    relationship_name,
                    {
                        "relationship_name": relationship_name,
                        "source_node_id": source_node_id,
                        "target_node_id": target_node_id,
                        "ontology_valid": False,
                        "edge_text": edge_text,
                    },
                )
            )
            existing_edges_map[edge_key] = True


def _process_wiki_entities(
    data_chunks: list,
    chunk_wikis: list,
    added_nodes_map: dict,
    existing_edges_map: dict,
) -> None:
    """Add contains edges for entities mentioned in ChunkWiki.key_entities.

    For each chunk, iterates over its wiki's key_entities and creates implicit
    contains edges for entities that are not already linked to the chunk.
    Entities are looked up from added_nodes_map by name.

    Args:
        data_chunks: List of DocumentChunk objects (modified in-place).
        chunk_wikis: List of ChunkWiki objects corresponding to each chunk.
        added_nodes_map: Mapping of node keys to Entity/EntityType objects.
        existing_edges_map: Mapping of edge keys to prevent duplicates.
    """
    if not chunk_wikis or not added_nodes_map:
        return

    for data_chunk, wiki in zip(data_chunks, chunk_wikis):
        if not wiki or not wiki.key_entities:
            continue

        existing_entity_names = set()
        if data_chunk.contains:
            for _, entity in data_chunk.contains:
                name = getattr(entity, "name", None)
                if name:
                    existing_entity_names.add(name)

        for entity_name in wiki.key_entities:
            if entity_name in existing_entity_names:
                continue

            entity_node = None
            for node in added_nodes_map.values():
                if getattr(node, "name", None) == entity_name:
                    entity_node = node
                    break

            if entity_node is None:
                continue

            if data_chunk.contains is None:
                data_chunk.contains = []

            edge_text = f"[wiki] Document chunk mentions {entity_name}"
            data_chunk.contains.append(
                (
                    Edge(
                        relationship_type="contains",
                        edge_text=edge_text,
                        implicit=False,
                        inference_layer="chunk",
                    ),
                    entity_node,
                )
            )


def _resolve_node(node_id: str, all_nodes: dict, key_mapping: dict):
    entity_key = key_mapping.get(f"{node_id}_entity", f"{node_id}_entity")
    type_key = key_mapping.get(f"{node_id}_type", f"{node_id}_type")
    return all_nodes.get(entity_key) or all_nodes.get(type_key)


def _populate_node_relations(all_nodes: dict, relationships: list, key_mapping: dict) -> None:
    """Attach edges to nodes via .relations for downstream traversal and persistence."""
    for src_id, tgt_id, rel_name, properties in relationships:
        src_node = _resolve_node(src_id, all_nodes, key_mapping)
        tgt_node = _resolve_node(tgt_id, all_nodes, key_mapping)

        if src_node is None or tgt_node is None:
            continue

        src_node.relations.append(
            (
                Edge(
                    relationship_type=rel_name,
                    edge_text=(properties or {}).get("edge_text"),
                ),
                tgt_node,
            )
        )


def expand_with_nodes_and_edges(
    data_chunks: list[DocumentChunk],
    chunk_graphs: list[KnowledgeGraph],
    ontology_resolver: BaseOntologyResolver = None,
    existing_edges_map: Optional[dict[str, bool]] = None,
    reject_unknown_entities: bool = False,
    chunk_wikis: Optional[list] = None,
):
    """Expand knowledge graphs with validated nodes and edges, integrating ontology information.

    This function processes document chunks and their associated knowledge graphs to create
    a comprehensive graph structure with entity nodes, entity type nodes, and their relationships.
    It validates entities against an ontology resolver and adds ontology-derived nodes and edges
    to enhance the knowledge representation.

    Args:
        data_chunks (list[DocumentChunk]): List of document chunks that contain the source data.
        chunk_graphs (list[KnowledgeGraph]): List of knowledge graphs corresponding to each
            data chunk. Each graph contains nodes (entities) and edges (relationships) extracted
            from the chunk content.
        ontology_resolver (BaseOntologyResolver, optional): Resolver for validating entities and
            types against an ontology. If None, a default RDFLibOntologyResolver is created.
        existing_edges_map (dict[str, bool], optional): Mapping of existing edge keys to prevent
            duplicate edge creation. If None, an empty dictionary is created.
        reject_unknown_entities (bool): If True, entities that don't match any ontology
            individual are silently dropped. If False (default), they are created as
            uncertain nodes with ontology_valid=False and no semantic edges.
        chunk_wikis (list[ChunkWiki], optional): List of ChunkWiki objects corresponding to
            each chunk. When provided, wiki.key_entities are used as additional sources for
            contains edges, improving entity coverage beyond raw-text LLM extraction.

    Returns:
        tuple[list, list]: A tuple containing:
            - graph_nodes (list): Combined list of data chunks and ontology nodes
            - graph_edges (list): List of edge tuples

    Note:
        - Entity nodes are created for each entity found in the knowledge graphs
        - EntityType nodes are created for each unique entity type
        - Ontology validation is performed to map entities to canonical ontology terms
        - Duplicate nodes and edges are prevented using internal mapping and the existing_edges_map
        - The function modifies data_chunks in-place by adding entities to their 'contains' attribute
        - When chunk_wikis is provided, wiki.key_entities are also added as contains edges

    """
    if existing_edges_map is None:
        existing_edges_map = {}

    if ontology_resolver is None:
        ontology_config = get_ontology_env_config()
        if (
            ontology_config.ontology_file_path
            and ontology_config.ontology_resolver
            and ontology_config.matching_strategy
        ):
            ontology_resolver = get_ontology_resolver_from_env(**ontology_config.to_dict())
        else:
            ontology_resolver = get_default_ontology_resolver()

    added_nodes_map = {}
    added_ontology_nodes_map = {}
    relationships = []
    ontology_relationships = []
    name_mapping = {}
    key_mapping = {}

    # Process each chunk and its corresponding graph
    for data_chunk, graph in zip(data_chunks, chunk_graphs):
        if not graph:
            continue

        # Process nodes first
        _process_graph_nodes(
            data_chunk,
            graph,
            ontology_resolver,
            added_nodes_map,
            added_ontology_nodes_map,
            name_mapping,
            key_mapping,
            existing_edges_map,
            ontology_relationships,
            reject_unknown_entities=reject_unknown_entities,
        )

        # Then process edges (with relationship whitelist filtering)
        _process_graph_edges(
            graph, name_mapping, existing_edges_map, relationships,
            added_nodes_map=added_nodes_map, key_mapping=key_mapping,
            ontology_resolver=ontology_resolver,
        )

    # Process ChunkWiki entities: add contains edges for entities mentioned in wiki
    if chunk_wikis:
        _process_wiki_entities(
            data_chunks, chunk_wikis, added_nodes_map, existing_edges_map,
        )

    all_nodes = {**added_nodes_map, **added_ontology_nodes_map}
    all_relationships = relationships + ontology_relationships
    _populate_node_relations(all_nodes, all_relationships, key_mapping)

    entity_nodes = list(added_nodes_map.values()) + list(added_ontology_nodes_map.values())

    return data_chunks, entity_nodes

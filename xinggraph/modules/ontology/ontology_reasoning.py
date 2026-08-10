"""Ontology reasoning utilities for query-time class hierarchy and explanation generation.

This module provides:
1. A class hierarchy cache that can expand ``is_a`` queries to include all
   ancestor classes (transitive closure).
2. A reasoning-chain generator that, given an entity, produces an explicit
   ontology-grounded explanation (e.g. "Audi_A8 is_a LuxuryCar; LuxuryCar
   subClassOf Car").
"""

from typing import Dict, List, Optional, Tuple
from xinggraph.shared.logging_utils import get_logger

logger = get_logger("OntologyReasoning")


class OntologyHierarchyCache:
    """Lightweight query-time cache over the ontology's class hierarchy.

    Usage::

        cache = OntologyHierarchyCache.from_ontology_resolver(resolver)
        # Check if entity_type matches or is a subclass of a query type
        cache.is_type_or_ancestor("ElectricCar", "Car")  # True
        # Get all ancestor types for an entity's declared type
        cache.get_all_ancestor_types("ElectricCar")  # ["Car"]
    """

    def __init__(self, hierarchy: Dict[str, List[str]] = None):
        """
        Args:
            hierarchy: {child_key: [ancestor_keys...]} transitive closure.
                       If None, an empty hierarchy is used.
        """
        self._hierarchy = hierarchy or {}
        # Pre-compute reverse map: ancestor -> set of descendants
        self._descendants: Dict[str, set] = {}
        for child, ancestors in self._hierarchy.items():
            for anc in ancestors:
                if anc not in self._descendants:
                    self._descendants[anc] = set()
                self._descendants[anc].add(child)

    @classmethod
    def from_ontology_resolver(cls, resolver) -> "OntologyHierarchyCache":
        """Build cache from an ontology resolver that implements ``get_class_hierarchy``."""
        try:
            hierarchy = resolver.get_class_hierarchy()
        except (NotImplementedError, AttributeError):
            logger.warning(
                "Ontology resolver does not support get_class_hierarchy(). "
                "Class hierarchy cache will be empty."
            )
            hierarchy = {}
        return cls(hierarchy)

    def is_type_or_ancestor(self, entity_type: str, query_type: str) -> bool:
        """Check if *entity_type* is the same as or a subclass of *query_type*.

        This implements the query-time保障: even if a direct ``is_a`` edge to
        ``query_type`` was missed during graph construction, this method will
        return True if the ontology says entity_type is a descendant of
        query_type.
        """
        norm_entity = entity_type.lower().replace(" ", "_").strip()
        norm_query = query_type.lower().replace(" ", "_").strip()

        if norm_entity == norm_query:
            return True

        ancestors = self._hierarchy.get(norm_entity, [])
        return norm_query in ancestors

    def get_all_ancestor_types(self, entity_type: str) -> List[str]:
        """Return all ancestor type keys for a given entity type."""
        norm = entity_type.lower().replace(" ", "_").strip()
        return list(self._hierarchy.get(norm, []))

    def get_all_descendant_types(self, class_name: str) -> List[str]:
        """Return all descendant type keys for a given class name."""
        norm = class_name.lower().replace(" ", "_").strip()
        return list(self._descendants.get(norm, set()))

    def get_type_chain(self, entity_type: str) -> List[str]:
        """Return the full type chain from entity_type up to root.

        Returns [entity_type, parent, grandparent, ...].
        """
        norm = entity_type.lower().replace(" ", "_").strip()
        chain = [norm]
        chain.extend(self._hierarchy.get(norm, []))
        return chain


def generate_ontology_reasoning_chain(
    entity_name: str,
    entity_type: str,
    ontology_resolver=None,
) -> str:
    """Generate a human-readable ontology reasoning chain for an entity.

    Example output::

        "Audi_A8 rdf:type LuxuryCar ; LuxuryCar rdfs:subClassOf Car"
    """
    if ontology_resolver is None:
        return f"{entity_name} rdf:type {entity_type}"

    try:
        type_chain = ontology_resolver.get_type_chain(entity_name)
    except (NotImplementedError, AttributeError):
        type_chain = []

    if not type_chain:
        # Fallback: just use the declared type
        try:
            ancestors = ontology_resolver.get_all_ancestors(entity_type)
        except (NotImplementedError, AttributeError):
            ancestors = []
        if ancestors:
            parts = [f"{entity_name} rdf:type {entity_type}"]
            prev = entity_type
            for anc in ancestors:
                parts.append(f"{prev} rdfs:subClassOf {anc}")
                prev = anc
            return " ; ".join(parts)
        return f"{entity_name} rdf:type {entity_type}"

    parts = []
    if len(type_chain) > 1:
        # type_chain is [entity, type1, type2, ..., root]
        parts.append(f"{type_chain[0]} rdf:type {type_chain[1]}")
        for i in range(1, len(type_chain) - 1):
            parts.append(f"{type_chain[i]} rdfs:subClassOf {type_chain[i+1]}")
    else:
        parts.append(f"{entity_name} rdf:type {entity_type}")

    return " ; ".join(parts)


def build_entity_ontology_context(
    entity_name: str,
    entity_type: str,
    ontology_resolver=None,
) -> Dict[str, any]:
    """Build a rich ontology context dict for a single entity.

    Returns dict with keys:
        - entity_name: str
        - entity_type: str
        - type_chain: List[str] (from entity up to root classes)
        - reasoning_chain: str (human-readable)
        - ontology_valid: bool
    """
    type_chain = []
    reasoning_chain = f"{entity_name} rdf:type {entity_type}"
    ontology_valid = False

    if ontology_resolver is not None:
        try:
            type_chain = ontology_resolver.get_type_chain(entity_name)
            ontology_valid = len(type_chain) > 1
        except (NotImplementedError, AttributeError):
            pass

        reasoning_chain = generate_ontology_reasoning_chain(
            entity_name, entity_type, ontology_resolver
        )

    return {
        "entity_name": entity_name,
        "entity_type": entity_type,
        "type_chain": type_chain,
        "reasoning_chain": reasoning_chain,
        "ontology_valid": ontology_valid,
    }

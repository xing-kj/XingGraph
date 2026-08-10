from typing import List, Optional

from xinggraph.infrastructure.engine import DataPoint
from xinggraph.modules.engine.models.EntityType import EntityType


class Entity(DataPoint):
    name: str
    is_a: Optional[EntityType] = None
    description: str
    relations: List[tuple] = []
    # Optional truth-alignment fields; never embedded (kept out of index_fields)
    # and not part of id/dedup (kept out of identity_fields).
    truth_alignment: Optional[list[float]] = None
    truth_subspace_signature: Optional[str] = None
    truth_epoch: Optional[int] = None
    # Ontology reasoning chain: e.g. "Audi_A8 rdf:type LuxuryCar ; LuxuryCar rdfs:subClassOf Car"
    # Populated during graph construction when an ontology is loaded.
    # Used at query time to provide ontology-grounded explanations.
    ontology_reasoning_chain: Optional[str] = None
    # identity_fields makes the id deterministic and namespaced by class
    # (``Entity:<name>``) when constructed without an explicit id — the same
    # value ``Entity.id_for(name)`` produces. Prevents the random-uuid4 footgun.
    metadata: dict = {"index_fields": ["name"], "identity_fields": ["name"]}

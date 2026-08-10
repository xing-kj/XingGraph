from abc import ABC, abstractmethod
from typing import List, Tuple, Optional, Dict

from xinggraph.modules.ontology.models import AttachedOntologyNode
from xinggraph.modules.ontology.matching_strategies import MatchingStrategy, FuzzyMatchingStrategy


class BaseOntologyResolver(ABC):
    """Abstract base class for ontology resolvers."""

    def __init__(self, matching_strategy: Optional[MatchingStrategy] = None):
        """Initialize the ontology resolver with a matching strategy.

        Args:
            matching_strategy: The strategy to use for entity matching.
                              Defaults to FuzzyMatchingStrategy if None.
        """
        self.matching_strategy = matching_strategy or FuzzyMatchingStrategy()

    @abstractmethod
    def build_lookup(self) -> None:
        """Build the lookup dictionary for ontology entities."""
        pass

    @abstractmethod
    def refresh_lookup(self) -> None:
        """Refresh the lookup dictionary."""
        pass

    @abstractmethod
    def find_closest_match(self, name: str, category: str) -> Optional[str]:
        """Find the closest match for a given name in the specified category."""
        pass

    @abstractmethod
    def get_subgraph(
        self, node_name: str, node_type: str = "individuals", directed: bool = True
    ) -> Tuple[
        List[AttachedOntologyNode], List[Tuple[str, str, str]], Optional[AttachedOntologyNode]
    ]:
        """Get a subgraph for the given node."""
        pass

    def get_class_hierarchy(self) -> Dict[str, List[str]]:
        """Return transitive class hierarchy {child_key: [ancestor_keys...]}.

        Optional method — raises NotImplementedError if not supported.
        """
        raise NotImplementedError("get_class_hierarchy not implemented")

    def get_all_ancestors(self, class_name: str) -> List[str]:
        """Get all ancestor class keys for a given class name.

        Optional method — raises NotImplementedError if not supported.
        """
        raise NotImplementedError("get_all_ancestors not implemented")

    def get_property_domain_range(self, property_name: str) -> Dict[str, List[str]]:
        """Get domain and range class keys for a given property.

        Returns {"domain": [class_keys], "range": [class_keys]}.
        Optional method — raises NotImplementedError if not supported.
        """
        raise NotImplementedError("get_property_domain_range not implemented")

    def get_object_properties(self) -> set:
        """Return the set of ObjectProperty keys declared in the ontology.

        Used as the whitelist for persisting LLM-extracted semantic edges
        (besides ``is_a``, which is always allowed). Optional method —
        returns an empty set if not supported, which means no non-is_a
        LLM edges are persisted.
        """
        return set()

    def is_subclass_of(self, child_name: str, parent_name: str) -> bool:
        """Check if child_name is a subclass of parent_name.

        Optional method — raises NotImplementedError if not supported.
        """
        raise NotImplementedError("is_subclass_of not implemented")

    def get_type_chain(self, entity_name: str) -> List[str]:
        """Get the full type chain for an entity.

        Optional method — raises NotImplementedError if not supported.
        """
        raise NotImplementedError("get_type_chain not implemented")

import os
import difflib
from xinggraph.shared.logging_utils import get_logger
from collections import deque
from typing import List, Tuple, Dict, Optional, Any, Union, IO
from rdflib import Graph, URIRef, RDF, RDFS, OWL, Namespace
from rdflib.util import guess_format

try:
    from rdflib.namespace import SKOS
except ImportError:
    SKOS = Namespace("http://www.w3.org/2004/02/skos/core#")

from xinggraph.modules.ontology.exceptions import (
    OntologyInitializationError,
    FindClosestMatchError,
    GetSubgraphError,
)
from xinggraph.modules.ontology.base_ontology_resolver import BaseOntologyResolver
from xinggraph.modules.ontology.models import AttachedOntologyNode
from xinggraph.modules.ontology.matching_strategies import MatchingStrategy, FuzzyMatchingStrategy

logger = get_logger("OntologyAdapter")

CONTENT_TYPE_FORMATS = {
    "application/rdf+xml": "xml",
    "application/xml": "xml",
    "text/xml": "xml",
    "text/turtle": "turtle",
    "application/x-turtle": "turtle",
    "text/n3": "n3",
    "application/n-triples": "nt",
    "application/n-quads": "nquads",
    "application/trig": "trig",
    "application/ld+json": "json-ld",
}

FALLBACK_FORMATS = ("xml", "turtle", "n3", "nt", "json-ld", "trig", "nquads")


class RDFLibOntologyResolver(BaseOntologyResolver):
    """RDFLib-based ontology resolver implementation.

    This implementation uses RDFLib to parse and work with RDF/OWL ontology files.
    It provides fuzzy matching and subgraph extraction capabilities for ontology entities.
    """

    def __init__(
        self,
        ontology_file: Optional[Union[str, List[str], IO, List[IO]]] = None,
        matching_strategy: Optional[MatchingStrategy] = None,
    ) -> None:
        super().__init__(matching_strategy)
        self.ontology_file = ontology_file
        try:
            self.graph = None
            if ontology_file is not None:
                files_to_load = []
                file_objects = []

                if hasattr(ontology_file, "read"):
                    file_objects = [ontology_file]
                elif isinstance(ontology_file, str):
                    files_to_load = [ontology_file]
                elif isinstance(ontology_file, list):
                    if all(hasattr(item, "read") for item in ontology_file):
                        file_objects = ontology_file
                    else:
                        files_to_load = ontology_file
                else:
                    raise ValueError(
                        f"ontology_file must be a string, list of strings, file-like object, list of file-like objects, or None. Got: {type(ontology_file)}"
                    )

                if file_objects:
                    self.graph = Graph()
                    loaded_objects = []
                    for file_obj in file_objects:
                        try:
                            parsed_format = self._parse_file_object(file_obj, self.graph)
                            loaded_objects.append(file_obj)
                            logger.info(
                                "Ontology loaded successfully from file object '%s' as %s",
                                self._get_file_object_name(file_obj),
                                parsed_format,
                            )
                        except Exception as e:
                            logger.warning(
                                "Failed to parse ontology file object '%s': %s",
                                self._get_file_object_name(file_obj),
                                str(e),
                            )

                    if not loaded_objects:
                        raise ValueError(
                            "No valid ontology file objects could be parsed. "
                            "No owl ontology will be attached to the graph."
                        )
                    else:
                        logger.info("Total ontology file objects loaded: %d", len(loaded_objects))

                elif files_to_load:
                    self.graph = Graph()
                    loaded_files = []
                    for file_path in files_to_load:
                        if os.path.exists(file_path):
                            self.graph.parse(file_path)
                            loaded_files.append(file_path)
                            logger.info("Ontology loaded successfully from file: %s", file_path)
                        else:
                            logger.warning(
                                "Ontology file '%s' not found. Skipping this file.",
                                file_path,
                            )

                    if not loaded_files:
                        logger.info(
                            "No valid ontology files found. No owl ontology will be attached to the graph."
                        )
                        self.graph = None
                    else:
                        logger.info("Total ontology files loaded: %d", len(loaded_files))
                else:
                    logger.info(
                        "No ontology file provided. No owl ontology will be attached to the graph."
                    )
            else:
                logger.info(
                    "No ontology file provided. No owl ontology will be attached to the graph."
                )
                self.graph = None

            self.build_lookup()
        except Exception as e:
            logger.error("Failed to load ontology", exc_info=True)
            raise OntologyInitializationError(f"Failed to load ontology: {e}") from e

    def _uri_to_key(self, uri: URIRef) -> str:
        uri_str = str(uri)
        if "#" in uri_str:
            name = uri_str.split("#")[-1]
        else:
            name = uri_str.rstrip("/").split("/")[-1]
        return name.lower().replace(" ", "_").strip()

    def _get_file_object_name(self, file_obj: IO) -> str:
        return str(
            getattr(file_obj, "filename", None)
            or getattr(file_obj, "name", None)
            or file_obj.__class__.__name__
        )

    def _get_content_type_format(self, file_obj: IO) -> Optional[str]:
        content_type = getattr(file_obj, "content_type", None)
        if not content_type:
            return None

        content_type = str(content_type).split(";", maxsplit=1)[0].strip().lower()
        return CONTENT_TYPE_FORMATS.get(content_type)

    def _get_candidate_formats(self, file_obj: IO) -> List[str]:
        formats = []

        filename = getattr(file_obj, "filename", None) or getattr(file_obj, "name", None)
        if filename:
            guessed_format = guess_format(str(filename))
            if guessed_format:
                formats.append(guessed_format)

        content_type_format = self._get_content_type_format(file_obj)
        if content_type_format:
            formats.append(content_type_format)

        formats.extend(FALLBACK_FORMATS)
        return list(dict.fromkeys(formats))

    def _parse_file_object(self, file_obj: IO, target_graph: Graph) -> str:
        try:
            file_obj.seek(0)
        except (AttributeError, OSError):
            pass

        content = file_obj.read()
        if not isinstance(content, (str, bytes)):
            raise TypeError(
                f"Ontology file object returned unsupported content type: {type(content)}"
            )

        candidate_formats = self._get_candidate_formats(file_obj)
        parse_errors = []

        for rdf_format in candidate_formats:
            parsed_graph = Graph()
            try:
                parsed_graph.parse(data=content, format=rdf_format)
            except Exception as error:
                parse_errors.append(f"{rdf_format}: {error}")
                continue

            for prefix, namespace in parsed_graph.namespaces():
                target_graph.bind(prefix, namespace, override=False)

            for triple in parsed_graph:
                target_graph.add(triple)

            return rdf_format

        raise ValueError(
            f"Unable to parse ontology file object '{self._get_file_object_name(file_obj)}'. "
            f"Tried formats: {', '.join(candidate_formats)}. "
            f"Last error: {parse_errors[-1] if parse_errors else 'unknown error'}"
        )

    def build_lookup(self) -> None:
        try:
            classes: Dict[str, URIRef] = {}
            individuals: Dict[str, URIRef] = {}
            label_index: Dict[str, URIRef] = {}  # rdfs:label / skos:altLabel -> URIRef

            if not self.graph:
                self.lookup: Dict[str, Dict[str, URIRef]] = {
                    "classes": classes,
                    "individuals": individuals,
                }
                self.label_index = label_index
                self._class_hierarchy: Dict[str, List[str]] = {}
                self._property_domain_range: Dict[str, Dict[str, List[str]]] = {}
                return None

            for cls in self.graph.subjects(RDF.type, OWL.Class):
                key = self._uri_to_key(cls)
                classes[key] = cls
                # Index rdfs:label as synonym
                for label in self.graph.objects(cls, RDFS.label):
                    label_key = str(label).lower().replace(" ", "_").strip()
                    if label_key and label_key != key:
                        label_index[label_key] = cls
                # Index skos:altLabel as synonym
                for alt in self.graph.objects(cls, SKOS.altLabel):
                    alt_key = str(alt).lower().replace(" ", "_").strip()
                    if alt_key and alt_key != key:
                        label_index[alt_key] = cls

            for subj, _, obj in self.graph.triples((None, RDF.type, None)):
                if obj in classes.values():
                    key = self._uri_to_key(subj)
                    individuals[key] = subj
                    # Index rdfs:label for individuals
                    for label in self.graph.objects(subj, RDFS.label):
                        label_key = str(label).lower().replace(" ", "_").strip()
                        if label_key and label_key != key:
                            label_index[label_key] = subj
                    for alt in self.graph.objects(subj, SKOS.altLabel):
                        alt_key = str(alt).lower().replace(" ", "_").strip()
                        if alt_key and alt_key != key:
                            label_index[alt_key] = subj

            self.lookup = {
                "classes": classes,
                "individuals": individuals,
            }
            self.label_index = label_index

            # Build transitive class hierarchy: {child_key: [ancestor_keys...]}
            self._class_hierarchy = self._build_class_hierarchy(classes)

            # Build property domain/range index
            self._property_domain_range = self._build_property_domain_range()

            logger.info(
                "Lookup built: %d classes, %d individuals, %d labels, %d hierarchy entries",
                len(classes),
                len(individuals),
                len(label_index),
                len(self._class_hierarchy),
            )

            return None
        except Exception as e:
            logger.error("Failed to build lookup dictionary: %s", str(e))
            raise RuntimeError("Lookup build failed") from e

    def _build_class_hierarchy(self, classes: Dict[str, URIRef]) -> Dict[str, List[str]]:
        """Build transitive closure of rdfs:subClassOf for all classes.

        Returns dict mapping each class key to its list of ancestor keys (root last).
        """
        hierarchy: Dict[str, List[str]] = {}
        for key, uri in classes.items():
            ancestors = []
            visited = set()
            queue = deque([uri])
            while queue:
                current = queue.popleft()
                for parent in self.graph.objects(current, RDFS.subClassOf):
                    parent_key = self._uri_to_key(parent)
                    if parent_key not in visited:
                        visited.add(parent_key)
                        ancestors.append(parent_key)
                        if parent in classes.values():
                            queue.append(parent)
            hierarchy[key] = ancestors
        return hierarchy

    def _build_property_domain_range(self) -> Dict[str, Dict[str, List[str]]]:
        """Build domain/range index for all ObjectProperties.

        Returns dict mapping property key -> {"domain": [class_keys], "range": [class_keys]}.
        """
        result: Dict[str, Dict[str, List[str]]] = {}
        for prop in self.graph.subjects(RDF.type, OWL.ObjectProperty):
            prop_key = self._uri_to_key(prop)
            domain_keys = []
            range_keys = []
            for domain_uri in self.graph.objects(prop, RDFS.domain):
                domain_keys.append(self._uri_to_key(domain_uri))
            for range_uri in self.graph.objects(prop, RDFS.range):
                range_keys.append(self._uri_to_key(range_uri))
            result[prop_key] = {"domain": domain_keys, "range": range_keys}
        return result

    def get_class_hierarchy(self) -> Dict[str, List[str]]:
        """Return the transitive class hierarchy {child: [ancestors...]}."""
        return self._class_hierarchy

    def get_all_ancestors(self, class_name: str) -> List[str]:
        """Get all ancestor class keys for a given class name (transitive closure)."""
        normalized = class_name.lower().replace(" ", "_").strip()
        return self._class_hierarchy.get(normalized, [])

    def get_property_domain_range(self, property_name: str) -> Dict[str, List[str]]:
        """Get domain and range class keys for a given property name."""
        normalized = property_name.lower().replace(" ", "_").strip()
        return self._property_domain_range.get(normalized, {"domain": [], "range": []})

    def get_object_properties(self) -> set:
        """Return the set of ObjectProperty keys declared in the ontology.

        Acts as the whitelist for persisting LLM-extracted semantic edges
        (besides ``is_a``, which is always allowed). Returns an empty set
        when no ontology is loaded, which blocks all non-is_a LLM edges.
        """
        if self.graph is None:
            return set()
        return {
            self._uri_to_key(prop)
            for prop in self.graph.subjects(RDF.type, OWL.ObjectProperty)
        }

    def is_subclass_of(self, child_name: str, parent_name: str) -> bool:
        """Check if child_name is a subclass of parent_name (direct or transitive)."""
        child_key = child_name.lower().replace(" ", "_").strip()
        parent_key = parent_name.lower().replace(" ", "_").strip()
        if child_key == parent_key:
            return True
        ancestors = self._class_hierarchy.get(child_key, [])
        return parent_key in ancestors

    def get_type_chain(self, entity_name: str) -> List[str]:
        """Get the full type chain for an entity (e.g., ['Audi_eTron', 'ElectricCar', 'Car'])."""
        normalized = entity_name.lower().replace(" ", "_").strip()
        # Try individuals first
        uri = self.lookup.get("individuals", {}).get(normalized)
        if uri is None:
            uri = self.lookup.get("classes", {}).get(normalized)
        if uri is None:
            # Check label index
            uri = self.label_index.get(normalized)
        if uri is None:
            return []

        chain = [normalized]
        visited = {normalized}
        queue = deque([uri])
        while queue:
            current = queue.popleft()
            for parent in self.graph.objects(current, RDFS.subClassOf):
                parent_key = self._uri_to_key(parent)
                if parent_key not in visited:
                    visited.add(parent_key)
                    chain.append(parent_key)
                    queue.append(parent)
            # For individuals, also follow rdf:type
            for parent in self.graph.objects(current, RDF.type):
                parent_key = self._uri_to_key(parent)
                if parent_key not in visited:
                    visited.add(parent_key)
                    chain.append(parent_key)
                    queue.append(parent)
        return chain

    def refresh_lookup(self) -> None:
        self.build_lookup()
        logger.info("Ontology lookup refreshed.")

    def find_closest_match(self, name: str, category: str) -> Optional[str]:
        try:
            normalized_name = name.lower().replace(" ", "_").strip()

            # 1. Exact match in primary lookup
            possible_matches = list(self.lookup.get(category, {}).keys())
            if normalized_name in possible_matches:
                return normalized_name

            # 2. Exact match in label index (rdfs:label / skos:altLabel)
            if normalized_name in self.label_index:
                uri = self.label_index[normalized_name]
                # Return the canonical key for this URI
                for key, val in self.lookup.get(category, {}).items():
                    if val == uri:
                        return key

            # 3. Fuzzy match in primary lookup
            result = self.matching_strategy.find_match(normalized_name, possible_matches)
            if result:
                return result

            # 4. Fuzzy match in label index
            label_matches = list(self.label_index.keys())
            label_result = self.matching_strategy.find_match(normalized_name, label_matches)
            if label_result:
                uri = self.label_index[label_result]
                for key, val in self.lookup.get(category, {}).items():
                    if val == uri:
                        return key

            return None
        except Exception as e:
            logger.error("Error in find_closest_match: %s", str(e))
            raise FindClosestMatchError() from e

    def _get_category(self, uri: URIRef) -> str:
        if uri in self.lookup.get("classes", {}).values():
            return "classes"
        if uri in self.lookup.get("individuals", {}).values():
            return "individuals"
        return "unknown"

    def get_subgraph(
        self, node_name: str, node_type: str = "individuals", directed: bool = True
    ) -> Tuple[
        List[AttachedOntologyNode], List[Tuple[str, str, str]], Optional[AttachedOntologyNode]
    ]:
        nodes_set = set()
        edges: List[Tuple[str, str, str]] = []
        visited = set()
        queue = deque()

        try:
            closest_match = self.find_closest_match(name=node_name, category=node_type)
            if not closest_match:
                logger.info("No close match found for '%s' in category '%s'", node_name, node_type)
                return [], [], None

            node = self.lookup[node_type].get(closest_match)
            if node is None:
                logger.info("Node '%s' not found in lookup.", closest_match)
                return [], [], None

            logger.info("%s match was found for found for '%s' node", node, node_name)

            queue.append(node)
            visited.add(node)
            nodes_set.add(node)

            obj_props = set(self.graph.subjects(RDF.type, OWL.ObjectProperty))

            while queue:
                current = queue.popleft()
                current_label = self._uri_to_key(current)

                if node_type == "individuals":
                    for parent in self.graph.objects(current, RDF.type):
                        parent_label = self._uri_to_key(parent)
                        edges.append((current_label, "is_a", parent_label))
                        if parent not in visited:
                            visited.add(parent)
                            queue.append(parent)
                        nodes_set.add(parent)

                for parent in self.graph.objects(current, RDFS.subClassOf):
                    parent_label = self._uri_to_key(parent)
                    edges.append((current_label, "is_a", parent_label))
                    if parent not in visited:
                        visited.add(parent)
                        queue.append(parent)
                    nodes_set.add(parent)

                for prop in obj_props:
                    prop_label = self._uri_to_key(prop)
                    for target in self.graph.objects(current, prop):
                        target_label = self._uri_to_key(target)
                        edges.append((current_label, prop_label, target_label))
                        if target not in visited:
                            visited.add(target)
                            queue.append(target)
                        nodes_set.add(target)
                    if not directed:
                        for source in self.graph.subjects(prop, current):
                            source_label = self._uri_to_key(source)
                            edges.append((source_label, prop_label, current_label))
                            if source not in visited:
                                visited.add(source)
                                queue.append(source)
                            nodes_set.add(source)

            rdf_nodes = [
                AttachedOntologyNode(uri=uri, category=self._get_category(uri))
                for uri in list(nodes_set)
            ]
            rdf_root = (
                AttachedOntologyNode(uri=node, category=self._get_category(node))
                if node is not None
                else None
            )

            return rdf_nodes, edges, rdf_root
        except Exception as e:
            logger.error("Error in get_subgraph: %s", str(e))
            raise GetSubgraphError() from e

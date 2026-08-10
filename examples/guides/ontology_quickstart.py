import asyncio
import xinggraph
import os
from xinggraph.modules.ontology.ontology_config import Config
from xinggraph.modules.ontology.rdf_xml.RDFLibOntologyResolver import RDFLibOntologyResolver


async def main():
    # Prune data and system metadata before running, only if we want "fresh" state.
    await xinggraph.forget(everything=True)

    texts = ["Audi produces the R8 and e-tron.", "Apple develops iPhone and MacBook."]

    ontology_path = os.path.join(
        os.path.dirname(os.path.abspath(__file__)), "ontology_input_example/basic_ontology.owl"
    )

    # Create full config structure manually
    config: Config = {
        "ontology_config": {
            "ontology_resolver": RDFLibOntologyResolver(ontology_file=ontology_path)
        }
    }

    await xinggraph.remember(texts, config=config, self_improvement=False)


if __name__ == "__main__":
    asyncio.run(main())

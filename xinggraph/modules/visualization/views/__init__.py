"""View modules for the xinggraph graph visualization.

Each submodule exports an ``emit_js(preprocessed) -> str`` function that
returns a JavaScript chunk. The orchestrator
(``xinggraph_network_visualization.py``) concatenates the chunks and
substitutes them into ``template.html`` via ``__TOKEN__`` placeholders.

The JS content for each view lives in a sibling ``.js`` file so it can be
maintained as JavaScript rather than as Python-string-escaped text.
"""

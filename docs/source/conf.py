project = "Dear Niece"
copyright = "2025, N. Papadakis"
author = "N. Papadakis"
release = "0.1.0"

extensions = [
    "myst_parser",
    "sphinxcontrib.mermaid",
    "sphinx.ext.mathjax",
]

myst_enable_extensions = [
    "colon_fence",
    "dollarmath",
    "deflist",
]

source_suffix = {
    ".rst": "restructuredtext",
    ".md": "markdown",
}

html_theme = "furo"
html_title = "Dear Niece"
exclude_patterns = ["_build", "Thumbs.db", ".DS_Store"]

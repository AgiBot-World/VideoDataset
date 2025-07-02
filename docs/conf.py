# Configuration file for the Sphinx documentation builder.
#
# This file only contains a selection of the most common options. For a full
# list see the documentation:
# https://www.sphinx-doc.org/en/master/usage/configuration.html

# -- Path setup --------------------------------------------------------------

# If extensions (or modules to document with autodoc) are in another directory,
# add these directories to sys.path here. If the directory is relative to the
# documentation root, use os.path.abspath to make it absolute, like shown here.
#
# import os
# import sys
# sys.path.insert(0, os.path.abspath('.'))
from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).parent.parent.resolve()

# -- Project information -----------------------------------------------------

project = "VideoDataset"
copyright = "2025 agibot"
author = "agibot"

# -- General configuration ---------------------------------------------------

# Add any Sphinx extension module names here, as strings. They can be
# extensions coming with Sphinx (named 'sphinx.ext.*') or your custom
# ones.
extensions = [
    "myst_parser",
    "sphinx.ext.autodoc",
    "sphinx.ext.intersphinx",
    "sphinx.ext.viewcode",
    "sphinx.ext.mathjax",
    "sphinx.ext.napoleon",
    "sphinx_autodoc_typehints",
    "sphinx_copybutton",
]
source_suffix = {
    ".rst": "restructuredtext",
    ".md": "markdown",
}
# Add any paths that contain templates here, relative to this directory.
templates_path = ["_templates"]

# List of patterns, relative to source directory, that match files and
# directories to ignore when looking for source files.
# This pattern also affects html_static_path and html_extra_path.
exclude_patterns = [
    "_build",
    "Thumbs.db",
    ".DS_Store",
    ".env",
    ".venv",
]

# https://www.sphinx-doc.org/en/master/usage/configuration.html#options-for-the-linkcheck-builder
linkcheck_ignore = [
    "https://code.agibot.com/ai-platform/videodataset",
    "https://pages.code.agibot.com/ai-platform/videodataset",
    "https://github.com",
    "https://docs.python.org",
]

# -- Options for HTML output -------------------------------------------------

# The theme to use for HTML and HTML Help pages.  See the documentation for
# a list of buhltin themes.
#
# default theme
# html_theme = 'alabaster'
#
# use furo
html_theme = "furo"

# Add any paths that contain custom static files (such as style sheets) here,
# relative to this directory. They are copied after the builtin static files,
# so a file named "default.css" will overwrite the builtin "default.css".
# html_static_path = ["_static"]

html_css_files = [
    "https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.5.1/css/fontawesome.min.css",
    "https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.5.1/css/solid.min.css",
    "https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.5.1/css/brands.min.css",
]

html_theme_options = {
    "footer_icons": [
        {
            "name": "GitLab",
            "url": "https://code.agibot.com/ai-platform/videodataset",
            "html": "",
            "class": "fa-brands fa-solid fa-gitlab fa-lg",
        },
    ],
}

# -- Extension configuration -------------------------------------------------
myst_enable_extensions = [
    "colon_fence",
    "substitution",
    "deflist",
]

# https://myst-parser.readthedocs.io/en/latest/syntax/optional.html#auto-generated-header-anchors
myst_heading_anchors = 3

intersphinx_mapping = {
    "python": ("https://docs.python.org/3", None),
}

nitpick_ignore = [
    ("py:class", "_io.StringIO"),
    ("py:class", "_io.BytesIO"),
]

always_document_param_types = True

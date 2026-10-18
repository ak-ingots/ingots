# Configuration file for the Sphinx documentation builder.
# https://www.sphinx-doc.org/en/master/usage/configuration.html

from importlib.metadata import version as _dist_version

# -- Project information ----------------------------------------------------

project = "Ingots"
author = "Aliaksandr Karotki"
copyright = f"2026, {author}"

# From the installed distribution: the static version in pyproject.toml.
# `release` is the full version, `version` the short X.Y.
release = _dist_version("ingots")
version = ".".join(release.split(".")[:2])

# -- General configuration --------------------------------------------------

extensions: list[str] = [
    "sphinx.ext.autodoc",
    "sphinx.ext.napoleon",
    "sphinx.ext.viewcode",
    "sphinx.ext.intersphinx",
    "sphinx_rtd_theme",
    "myst_parser",
]

templates_path: list[str] = ["_templates"]
exclude_patterns: list[str] = ["build", "Thumbs.db", ".DS_Store"]

# Markdown (MyST) sources alongside reStructuredText.
myst_enable_extensions = ["colon_fence", "deflist"]
myst_heading_anchors = 3

autodoc_typehints = "description"
autodoc_member_order = "bysource"
# Document each object once, at its definition site: an automodule on a
# package __init__ otherwise re-documents the names it re-exports in __all__.
autodoc_default_options = {"ignore-module-all": True}

intersphinx_mapping = {"python": ("https://docs.python.org/3", None)}

# -- HTML output ------------------------------------------------------------

html_theme = "sphinx_rtd_theme"
html_static_path: list[str] = ["static"]
# Trims the "On Read the Docs" section out of the Addons flyout menu; see the
# file for why this cannot be done with CSS or a project setting.
html_js_files: list[str] = ["rtd-flyout.js"]
html_title = f"{project} {release}"
html_theme_options = {
    "navigation_depth": 3,
    "collapse_navigation": False,
}

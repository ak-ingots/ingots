# Configuration file for the Sphinx documentation builder.
# https://www.sphinx-doc.org/en/master/usage/configuration.html

import os.path
import typing as t
from importlib.metadata import version as _dist_version

from sphinx.domains.python import PythonDomain

if t.TYPE_CHECKING:
    from sphinx.application import Sphinx
    from sphinx.domains.python import ObjectEntry
    from sphinx.environment import BuildEnvironment

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


# -- Cross-references -------------------------------------------------------


class _NearestPythonDomain(PythonDomain):
    """
    Resolves a short name with several targets to the one nearest to the
    referring module: a forward-referenced ``"Project"`` in ``ingots.puer``
    is ``ingots.puer.project.Project``, in ``ingots.defaults`` it is
    ``ingots.defaults.project.Project``.
    """

    @t.override
    def find_obj(
        self,
        env: "BuildEnvironment",
        modname: str,
        classname: str,
        name: str,
        type: str | None,
        searchmode: int = 0,
    ) -> "list[tuple[str, ObjectEntry]]":
        matches = super().find_obj(env, modname, classname, name, type, searchmode)
        if len(matches) < 2 or not modname:
            return matches

        def nearness(match: "tuple[str, ObjectEntry]") -> int:
            prefix = os.path.commonprefix([modname.split("."), match[0].split(".")])
            return len(prefix)

        nearest = max(map(nearness, matches))
        return [match for match in matches if nearness(match) == nearest]


def setup(app: "Sphinx") -> None:
    app.add_domain(_NearestPythonDomain, override=True)

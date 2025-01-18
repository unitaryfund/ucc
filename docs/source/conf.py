import os
import sys

sys.path.insert(0, os.path.abspath('..'))
sys.path.insert(0, os.path.abspath('../../'))
sys.path.insert(0, os.path.abspath('../../../'))


project = "ucc"
copyright = "2024, Unitary Foundation"
author = "Unitary Foundation"
directory_of_this_file = os.path.dirname(os.path.abspath(__file__))
with open(f"{directory_of_this_file}/../../VERSION.txt", "r") as f:
    release = f.read().strip()

# -- General configuration ---------------------------------------------------
# https://www.sphinx-doc.org/en/master/usage/configuration.html#general-configuration

extensions = ["sphinx.ext.napoleon", "sphinx.ext.autodoc", "myst_parser"]
# Suppress warnings related to heading levels
suppress_warnings = [
    'myst.header'
]

# Optionally, enable cross-referencing for `.rst` files as well
myst_crossref = True

templates_path = ["_templates"]
exclude_patterns = ["_build", "Thumbs.db", ".DS_Store"]

source_suffix = [".rst", ".md"]  # Allow Sphinx to process both .rst and .md files


# -- Options for HTML output -------------------------------------------------
# https://www.sphinx-doc.org/en/master/usage/configuration.html#options-for-html-output

html_theme = "alabaster"
html_static_path = []

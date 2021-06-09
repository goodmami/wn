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


# -- Project information -----------------------------------------------------

project = 'wn'
copyright = '2020, Michael Wayne Goodman'
author = 'Michael Wayne Goodman'

import wn

# The short X.Y version
version = '.'.join(wn.__version__.split('.')[:2])
# The full version, including alpha/beta/rc tags
release = wn.__version__

# -- General configuration ---------------------------------------------------

# Add any Sphinx extension module names here, as strings. They can be
# extensions coming with Sphinx (named 'sphinx.ext.*') or your custom
# ones.
extensions = [
    'sphinx.ext.autodoc',
    'sphinx.ext.intersphinx',
    'sphinx.ext.coverage',
    # 'sphinx.ext.viewcode',
    'sphinx.ext.githubpages',
    'sphinx.ext.napoleon',
    "sphinx_copybutton",
]

# Add any paths that contain templates here, relative to this directory.
templates_path = ['_templates']

# List of patterns, relative to source directory, that match files and
# directories to ignore when looking for source files.
# This pattern also affects html_static_path and html_extra_path.
exclude_patterns = ['_build', 'Thumbs.db', '.DS_Store']

# Global definitions
rst_prolog = """
.. role:: python(code)
   :language: python
   :class: highlight
"""

# smartquotes = False
smartquotes_action = 'De'  # D = en- and em-dash; e = ellipsis

# -- Options for HTML output -------------------------------------------------

# The theme to use for HTML and HTML Help pages.  See the documentation for
# a list of builtin themes.#

html_theme = "furo"
html_theme_options = {
    "light_css_variables": {
        "color-brand-primary": "#006699",
        "color-brand-content": "#006699",
        # "color-background": "#f0f0f0",
        # "color-sidebar-background": "#ddd",
    },
    "dark_css_variables": {
        "color-brand-primary": "#00CCFF",
        "color-brand-content": "#00CCFF",
    }
}

html_logo = "_static/wn-logo.svg"

pygments_style = 'manni'
pygments_dark_style = 'monokai'

# Add any paths that contain custom static files (such as style sheets) here,
# relative to this directory. They are copied after the builtin static files,
# so a file named "default.css" will overwrite the builtin "default.css".
html_static_path = ['_static']
html_css_files = [
    'css/svg.css',
]

# Don't offer to show the source of the current page
html_show_sourcelink = False

# -- Options for autodoc extension -------------------------------------------

autodoc_typehints = 'description'
# autodoc_typehints = 'signature'
# autodoc_typehints = 'none'

# -- Options for intersphinx extension ---------------------------------------

# Example configuration for intersphinx: refer to the Python standard library.
intersphinx_mapping = {
    'python': ('https://docs.python.org/3', None),
    'requests': ('https://requests.readthedocs.io/en/master/', None),
}

# -- Options for sphinx_copybutton extension ---------------------------------

copybutton_prompt_text = (
    r">>> "              # regular Python prompt
    r"|\.\.\. "          # Python continuation prompt
    r"|\$ "              # Basic shell
    r"|In \[\d*\]: "     # Jupyter notebook
)
copybutton_prompt_is_regexp = True

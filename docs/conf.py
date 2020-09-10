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

import wn._meta

# The short X.Y version
version = '.'.join(wn._meta.__version__.split('.')[:2])
# The full version, including alpha/beta/rc tags
release = wn._meta.__version__

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

pygments_style = 'manni'

# -- Options for HTML output -------------------------------------------------

# The theme to use for HTML and HTML Help pages.  See the documentation for
# a list of builtin themes.
#
# html_theme = 'sphinx_material'
# html_theme_options = {
#     'base_url': 'http://goodmami.github.io/wn/',
#     'repo_url': 'https://github.com/goodmami/wn/',
#     'repo_name': 'wn',
#     # 'google_analytics_account': 'UA-XXXXX',
#     'html_minify': True,
#     'css_minify': True,
#     'nav_title': 'wn',
#     'logo_icon': '&#xe869',
#     'color_primary': 'teal',
#     'color_accent': 'deep-orange',
#     'globaltoc_depth': 2,
# }

html_theme = "furo"
html_theme_options = {
    "css_variables": {
        # "color-brand-primary": "red",
        # "color-brand-content": "#CC3333",
        # "color-background": "#f0f0f0",
        # "color-sidebar-background": "#ddd",
    }
}

# Add any paths that contain custom static files (such as style sheets) here,
# relative to this directory. They are copied after the builtin static files,
# so a file named "default.css" will overwrite the builtin "default.css".
html_static_path = ['_static']

# Don't offer to show the source of the current page
html_show_sourcelink = False

# -- Options for autodoc extension -------------------------------------------

# disable type hints

autodoc_typehints = 'none'

# -- Options for sphinx_copybutton extension ---------------------------------

copybutton_prompt_text = (
    r">>> "              # regular Python prompt
    r"|\.\.\. "          # Python continuation prompt
    r"|\$ "              # Basic shell
    r"|In \[\d*\]: "     # Jupyter notebook
)
copybutton_prompt_is_regexp = True

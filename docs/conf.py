import os
import sys
sys.path.insert(0, os.path.abspath('../src')) # Adjust if your source code folder is different from src

project = 'Automagik Agents'
copyright = '2024, Namastex Labs' # Adapt with the year and your name/organization
author = 'Namastex Labs' # Adapt with your name/organization

# The short X.Y version
# version = '0.1' # You might want to get this from your __version__
# The full version, including alpha/beta/rc tags
# release = '0.1.0' # You might want to get this from your __version__

extensions = [
    'sphinx.ext.autodoc',      # Include documentation from docstrings
    'sphinx.ext.napoleon',     # Support for Google and NumPy style docstrings
    'sphinx.ext.viewcode',     # Add links to source code
    'sphinx.ext.githubpages',  # Helps with publishing to GitHub Pages
    'myst_parser',             # To be able to use Markdown
    'sphinx_rtd_theme',        # Read the Docs theme
]

# Napoleon settings (if you use Google/NumPy style docstrings)
napoleon_google_docstring = True
napoleon_numpy_docstring = True
napoleon_include_init_with_doc = False
napoleon_include_private_with_doc = False
napoleon_include_special_with_doc = True
napoleon_use_admonition_for_examples = False
napoleon_use_admonition_for_notes = False
napoleon_use_admonition_for_references = False
napoleon_use_ivar = False
napoleon_use_param = True
napoleon_use_rtype = True

# myst_parser settings (optional, to enable more Markdown features)
myst_enable_extensions = [
    "colon_fence",
    "amsmath",
    "dollarmath",
    "linkify",
    "smartquotes",
    "substitution",
]

templates_path = ['_templates']
exclude_patterns = ['_build', 'Thumbs.db', '.DS_Store']

language = 'en' # Or 'pt_BR' if you prefer

html_theme = 'sphinx_rtd_theme'
html_static_path = ['_static']

# Add any paths that contain custom templates here, relative to this directory.
# templates_path = ['_templates']

# If true, the current module name will be prepended to all description
# unit titles (such as .. function::).
# add_module_names = True

# -- Options for autodoc ---
autodoc_member_order = 'bysource' # Keeps the source code order
# autodoc_default_options = {
# 'members': True,
# 'undoc-members': True,
# 'private-members': False,
# 'special-members': '__init__',
# 'inherited-members': True,
# 'show-inheritance': True,
# }

# For viewcode to work correctly, you might need to adjust
# the following if your code is not in the root along with the docs folder
# import inspect
# for modname, module in sys.modules.items():
# try:
#     if module.__file__.startswith(os.path.abspath('..')):
#         if hasattr(module, '__path__'):
#             for _, path, _ in pkgutil.walk_packages(module.__path__):
#                 sys.modules[modname + '.' + path].__file__ = module.__file__
#         else:
#             sys.modules[modname].__file__ = module.__file__
# except (AttributeError, KeyError):
#     pass 
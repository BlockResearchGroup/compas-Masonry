import os

title = "COMPAS Masonry"
designers = []
developers = ["Tom Van Mele", "Alessandro Dell'Endice"]
documenters = []
description = """
"""
website = "https://gitbook.com/blockresearchgroup/compas-Masonry"

__author__ = ["tom van mele"]
__copyright__ = "ETH Zurich - Block Research Group"
__license__ = "MIT License"
__email__ = "tom.v.mele@gmail.com"
__version__ = "0.1.0"


HERE = os.path.dirname(__file__)

HOME = os.path.abspath(os.path.join(HERE, "../../"))
DATA = os.path.abspath(os.path.join(HOME, "data"))
DOCS = os.path.abspath(os.path.join(HOME, "docs"))
TEMP = os.path.abspath(os.path.join(HOME, "temp"))


__all__ = ["HOME", "DATA", "DOCS", "TEMP"]

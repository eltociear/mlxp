

VERSION = (0, 1, 0)
PROJECT = "MLXP"
AUTHOR = "Michael Arbel"
AUTHOR_EMAIL = "michael.n.arbel@gmail.com"
URL = "https://github.com/inria-thoth/mlxp"
LICENSE = "MIT License"
VERSION_TEXT = ".".join(str(x) for x in VERSION)
COPYRIGHT = "Copyright (C) 2023 " + AUTHOR


VERSION_STATUS = ""
RELEASE = VERSION_TEXT + VERSION_STATUS


__version__ = VERSION_TEXT
__author__ = AUTHOR
__copyright__ = COPYRIGHT
__credits__ = [
    "Romain Ménégaux",
    "Alexandre Zouaoui",
    "Juliette Marrie",
    "Pierre Wolinski",
]
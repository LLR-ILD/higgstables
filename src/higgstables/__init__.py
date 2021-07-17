"""Create category-decay tables in the input format for `alldecays`.

As input, root files as produced in `make_event_vector` of the `Higgs-BR-classes` repository are expected.
Further information:
* Code: https://github.com/LLR-ILD/higgstables
* alldecays: https://github.com/LLR-ILD/alldecays
* Higgs-BR-classes: https://github.com/LLR-ILD/Higgs-BR-classes
"""
import logging

from .config import Config
from .handle_root_files import FileToCounts, TablesFromFiles
from .ild_specific import CrossSections
from .version import __version__

_version_info = f"{__name__} version {__version__} at {__file__[:-len('/__init__.py')]}"
logger = logging.getLogger(__name__)
logger.debug(_version_info)

__all__ = [
    "Config",
    "CrossSections",
    "FileToCounts",
    "TablesFromFiles",
    "__version__",
]

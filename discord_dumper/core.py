"""Core module."""

from importlib.metadata import Distribution

_DISTRIBUTION = Distribution.from_name("discord_dumper")
_METADATA = _DISTRIBUTION.metadata

__author__ = _METADATA["Author"]
__email__ = _METADATA["Author-email"]
__license__ = _METADATA["License"]
__version__ = _METADATA["Version"]
__maintainer__ = _METADATA["Maintainer"]
__summary__ = _METADATA["Summary"]
__copyright__ = f"{__author__} <{__email__}>"
__issues__ = "https://github.com/Dashstrom/discord-dumper/issues"

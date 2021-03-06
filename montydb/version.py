
VERSION_MAJOR = 2
VERSION_MINOR = 3
VERSION_PATCH = 2

version_info = (VERSION_MAJOR, VERSION_MINOR, VERSION_PATCH)
version = "%i.%i.%i" % version_info
__version__ = version


MONGO_VER_MAJOR = 4
MONGO_VER_MINOR = 2
MONGO_VER_PATCH = 10

mongo_version_info = (MONGO_VER_MAJOR, MONGO_VER_MINOR, MONGO_VER_PATCH)
mongo_version = "%i.%i.%i" % mongo_version_info

__all__ = (
    "version",
    "version_info",
    "mongo_version",
    "mongo_version_info",
    "__version__",
)

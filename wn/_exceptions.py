
class Error(Exception):
    """Generic error class for invalid wordnet operations."""

    # reset the module so the user sees the public name
    __module__ = 'wn'


class DatabaseError(Error):
    """Error class for issues with the database."""

    __module__ = 'wn'


class ConfigurationError(Error):
    """Raised on invalid configurations."""
    __module__ = 'wn'


class ProjectError(Error):
    """Raised when a project is not found or on errors defined in the index."""
    __module__ = 'wn'


class WnWarning(Warning):
    """Generic warning class for dubious wordnet operations."""

    # reset the module so the user sees the public name
    __module__ = 'wn'


class Error(Exception):
    """Generic error class for invalid wordnet operations."""

    # reset the module so the user sees the public name
    __module__ = 'wn'


class DatabaseError(Error):
    """Error class for issues with the database."""

    __module__ = 'wn'


class WnWarning(Warning):
    """Generic warning class for dubious worndet operations."""

    # reset the module so the user sees the public name
    __module__ = 'wn'

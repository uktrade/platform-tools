# This exception exists so that we can easily catch exceptions
# at the command level where we know we can just output the
# error and abort.
class PlatformException(Exception):
    pass


class ValidationException(PlatformException):
    pass

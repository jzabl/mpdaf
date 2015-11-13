import functools
import inspect
import warnings
from astropy.units import UnitsWarning


# NOTE(kgriffs): We don't want our deprecations to be ignored by default,
# so create our own type.
class MpdafWarning(UserWarning):
    pass


class MpdafUnitsWarning(UnitsWarning):
    pass


def deprecated(instructions):
    """Flags a method as deprecated.

    Args:
        instructions: A human-friendly string of instructions, such
            as: 'Please migrate to add_proxy() ASAP.'
    """
    def decorator(func):
        """This is a decorator which can be used to mark functions as
        deprecated.

        It will result in a warning being emitted when the function is
        used.
        """
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            message = 'Call to deprecated function `{}`. {}'.format(
                func.__name__,
                instructions)

            frame = inspect.currentframe().f_back
            warnings.warn_explicit(message,
                                   category=MpdafWarning,
                                   filename=inspect.getfile(frame.f_code),
                                   lineno=frame.f_lineno)
            return func(*args, **kwargs)
        return wrapper
    return decorator

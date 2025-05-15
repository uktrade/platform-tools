import functools
import time
from typing import Callable
from typing import Optional

from dbt_platform_helper.platform_exception import PlatformException
from dbt_platform_helper.providers.io import ClickIOProvider

SECONDS_BEFORE_RETRY = 3
RETRY_MAX_ATTEMPTS = 3


class RetryException(PlatformException):

    def __init__(
        self, function_name: str, max_attempts: int, original_exception: Optional[Exception] = None
    ):
        message = f"Function: {function_name} failed after {max_attempts} attempts"
        self.original_exception = original_exception
        if original_exception:
            message += f": \n{str(original_exception)}"
        super().__init__(message)


def retry(
    exceptions_to_catch: tuple = (Exception,),
    max_attempts: int = RETRY_MAX_ATTEMPTS,
    delay: float = SECONDS_BEFORE_RETRY,
    raise_custom_exception: bool = True,
    custom_exception: type = RetryException,
    io: ClickIOProvider = ClickIOProvider(),
):
    def decorator(func):
        func.__wrapped_by__ = "retry"

        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            last_exception = None
            for attempt in range(max_attempts):
                try:
                    return func(*args, **kwargs)
                except exceptions_to_catch as e:
                    last_exception = e
                    io.debug(
                        f"Attempt {attempt+1}/{max_attempts} for {func.__name__} failed with exception {str(last_exception)}"
                    )
                    if attempt < max_attempts - 1:
                        time.sleep(delay)
            if raise_custom_exception:
                raise custom_exception(func.__name__, max_attempts, last_exception)
            raise last_exception

        return wrapper

    return decorator


def wait_until(
    exceptions_to_catch: tuple = (PlatformException,),
    max_attempts: int = RETRY_MAX_ATTEMPTS,
    delay: float = SECONDS_BEFORE_RETRY,
    raise_custom_exception: bool = True,
    custom_exception=RetryException,
    message_on_false="Condition not met",
    io: ClickIOProvider = ClickIOProvider(),
):
    """Wrap a function which returns a boolean."""

    def decorator(func: Callable[..., bool]):
        func.__wrapped_by__ = "wait_until"

        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            last_exception = None
            for attempt in range(max_attempts):
                try:
                    result = func(*args, **kwargs)
                    if result:
                        return result
                    io.debug(
                        f"Attempt {attempt+1}/{max_attempts} for {func.__name__} returned falsy"
                    )
                except exceptions_to_catch as e:
                    last_exception = e
                    io.debug(
                        f"Attempt {attempt+1}/{max_attempts} for {func.__name__} failed with exception {str(last_exception)}"
                    )

                if attempt < max_attempts - 1:
                    time.sleep(delay)

            if not last_exception:  # If func returns false set last_exception
                last_exception = PlatformException(message_on_false)
            if (
                not raise_custom_exception
            ):  # Raise last_exception when you don't want custom exception
                raise last_exception
            else:
                raise custom_exception(func.__name__, max_attempts, last_exception)

        return wrapper

    return decorator

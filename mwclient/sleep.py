import time
import logging
from mwclient.errors import MaximumRetriesExceeded

log = logging.getLogger(__name__)


class Sleepers(object):
    """
    A class that allows for the creation of multiple `Sleeper` objects with shared
    arguments.
    Examples:
        Firstly a `Sleepers` object containing the shared attributes has to be created.
        >>> max_retries, retry_timeout = 5, 5
        >>> sleepers = Sleepers(max_retries, retry_timeout)
        From this `Sleepers` object multiple individual `Sleeper` objects can be created
        using the `make` method.
        >>> sleeper = sleepers.make()
    Args:
        max_retries (int): The maximum number of retries to perform.
        retry_timeout (int): The time to sleep for each past retry.
        callback (Callable[[int, Any], None]): A callable to be called on each retry.
    Attributes:
        max_retries (int): The maximum number of retries to perform.
        retry_timeout (int): The time to sleep for each past retry.
        callback (callable): A callable to be called on each retry.
    """
    def __init__(self, max_retries, retry_timeout, callback=lambda *x: None):
        self.max_retries = max_retries
        self.retry_timeout = retry_timeout
        self.callback = callback

    def make(self, args=None):
        """
        Creates a new `Sleeper` object.
        Args:
            args (Any): Arguments to be passed to the `callback` callable.
        Returns:
            Sleeper: A `Sleeper` object.
        """
        return Sleeper(args, self.max_retries, self.retry_timeout, self.callback)


class Sleeper(object):
    """
    For any given operation, a `Sleeper` object keeps count of the number of retries.
    For each retry, the sleep time increases until the max number of retries is reached
    and a `MaximumRetriesExceeded` is raised. The sleeper object should be discarded
    once the operation is successful.
    Args:
        args (Any): Arguments to be passed to the `callback` callable.
        max_retries (int): The maximum number of retries to perform.
        retry_timeout (int): The time to sleep for each past retry.
        callback (callable, None]): A callable to be called on each retry.
    Attributes:
        args (Any): Arguments to be passed to the `callback` callable.
        retries (int): The number of retries that have been performed.
        max_retries (int): The maximum number of retries to perform.
        retry_timeout (int): The time to sleep for each past retry.
        callback (callable): A callable to be called on each retry.
    """
    def __init__(self, args, max_retries, retry_timeout, callback):
        self.args = args
        self.retries = 0
        self.max_retries = max_retries
        self.retry_timeout = retry_timeout
        self.callback = callback

    def sleep(self, min_time=0):
        """
        Sleeps for a minimum of `min_time` seconds. The actual sleeping time will increase
        with the number of retries.
        Args:
            min_time (int): The minimum sleeping time.
        Raises:
            MaximumRetriesExceeded: If the number of retries exceeds the maximum.
        """
        self.retries += 1
        if self.retries > self.max_retries:
            raise MaximumRetriesExceeded(self, self.args)

        self.callback(self, self.retries, self.args)

        timeout = self.retry_timeout * (self.retries - 1)
        if timeout < min_time:
            timeout = min_time
        log.debug('Sleeping for %d seconds', timeout)
        time.sleep(timeout)

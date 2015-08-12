import time
import logging
from mwclient.errors import MaximumRetriesExceeded

log = logging.getLogger(__name__)


class Sleepers(object):

    def __init__(self, max_retries, retry_timeout, callback=lambda *x: None):
        self.max_retries = max_retries
        self.retry_timeout = retry_timeout
        self.callback = callback

    def make(self, args=None):
        return Sleeper(args, self.max_retries, self.retry_timeout, self.callback)


class Sleeper(object):
    """
    For any given operation, a `Sleeper` object keeps count of the number of
    retries. For each retry, the sleep time increases until the max number of
    retries is reached and a `MaximumRetriesExceeded` is raised. The sleeper
    object should be discarded once the operation is successful.
    """

    def __init__(self, args, max_retries, retry_timeout, callback):
        self.args = args
        self.retries = 0
        self.max_retries = max_retries
        self.retry_timeout = retry_timeout
        self.callback = callback

    def sleep(self, min_time=0):
        """
        Sleep a minimum of `min_time` seconds.
        The actual sleeping time will increase with the number of retries.
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

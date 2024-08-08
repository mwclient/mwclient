import time
import io
import warnings


def parse_timestamp(t):
    """Parses a string containing a timestamp.

    Args:
        t (str): A string containing a timestamp.

    Returns:
        time.struct_time: A timestamp.
    """
    if t is None or t == '0000-00-00T00:00:00Z':
        return time.struct_time((0, 0, 0, 0, 0, 0, 0, 0, 0))
    return time.strptime(t, '%Y-%m-%dT%H:%M:%SZ')


def read_in_chunks(stream, chunk_size):
    while True:
        data = stream.read(chunk_size)
        if not data:
            break
        yield io.BytesIO(data)


def handle_limit(limit, max_items, api_chunk_size):
    """
    Consistently handles 'limit', 'api_chunk_size' and 'max_items' -
    https://github.com/mwclient/mwclient/issues/259 . In version 0.11,
    'api_chunk_size' was introduced as a better name for 'limit', but
    we still accept 'limit' with a deprecation warning. 'max_items'
    does what 'limit' sounds like it should.
    """
    if limit:
        if api_chunk_size:
            warnings.warn(
                "limit and api_chunk_size both specified, this is not supported! limit "
                "is deprecated, will use value of api_chunk_size",
                DeprecationWarning
            )
        else:
            warnings.warn(
                "limit is deprecated as its name and purpose are confusing. use "
                "api_chunk_size to set the number of items retrieved from the API at "
                "once, and/or max_items to limit the total number of items that will be "
                "yielded",
                DeprecationWarning
            )
            api_chunk_size = limit
    return (max_items, api_chunk_size)

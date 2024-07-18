import time
import io
from typing import Optional, Iterable


def parse_timestamp(t: Optional[str]) -> time.struct_time:
    """Parses a string containing a timestamp.

    Args:
        t: A string containing a timestamp.

    Returns:
        time.struct_time: A timestamp.
    """
    if t is None or t == '0000-00-00T00:00:00Z':
        return time.struct_time((0, 0, 0, 0, 0, 0, 0, 0, 0))
    return time.strptime(t, '%Y-%m-%dT%H:%M:%SZ')


def read_in_chunks(stream: io.BufferedReader, chunk_size: int) -> Iterable[io.BytesIO]:
    while True:
        data = stream.read(chunk_size)
        if not data:
            break
        yield io.BytesIO(data)

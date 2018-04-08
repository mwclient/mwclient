import time
import io


def parse_timestamp(t):
    if t is None or t == '0000-00-00T00:00:00Z':
        return (0, 0, 0, 0, 0, 0, 0, 0, 0)
    return time.strptime(t, '%Y-%m-%dT%H:%M:%SZ')


def read_in_chunks(stream, chunk_size):
    while True:
        data = stream.read(chunk_size)
        if not data:
            break
        yield io.BytesIO(data)

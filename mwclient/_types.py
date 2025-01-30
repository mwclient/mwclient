from http.cookiejar import CookieJar
from typing import Union, Tuple, Mapping

Cookies = Union[Mapping[str, str], CookieJar]

Namespace = Union[str, int]

VersionTuple = Tuple[Union[int, str], ...]

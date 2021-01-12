from typing import Optional

from multidict import CIMultiDictProxy, CIMultiDict


EMPTY_HEADERS = CIMultiDictProxy[str](CIMultiDict[str]())


def get_headers_to_enrich(headers: Optional[CIMultiDictProxy[str]]) -> CIMultiDict[str]:
    return CIMultiDict[str](headers) if headers is not None else CIMultiDict[str]()

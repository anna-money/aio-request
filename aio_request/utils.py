from multidict import CIMultiDictProxy, CIMultiDict


def empty_close() -> None:
    ...


EMPTY_HEADERS = CIMultiDictProxy[str](CIMultiDict[str]())

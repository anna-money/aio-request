from multidict import CIMultiDictProxy, CIMultiDict


EMPTY_HEADERS = CIMultiDictProxy[str](CIMultiDict[str]())

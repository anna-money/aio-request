import contextlib
import contextvars
from typing import Iterator, Optional, Union, cast

from .deadline import Deadline
from .priority import Priority

sentinel = object()


class Context:
    __slots__ = ("deadline", "priority")

    def __init__(
        self,
        deadline: Optional[Deadline] = None,
        priority: Optional[Priority] = None,
    ):
        self.deadline: Optional[Deadline] = deadline
        self.priority: Optional[Priority] = priority

    def set(
        self,
        deadline: Optional[Union[Deadline, object]] = sentinel,
        priority: Optional[Union[Priority, object]] = sentinel,
    ) -> "Context":
        return Context(
            deadline=self.deadline if deadline is sentinel else cast(Optional[Deadline], deadline),
            priority=self.priority if priority is sentinel else cast(Optional[Priority], priority),
        )


context_var = contextvars.ContextVar("aio_request.context", default=Context())


@contextlib.contextmanager
def set_context(
    *,
    deadline: Optional[Union[Deadline, object]] = sentinel,
    priority: Optional[Union[Deadline, object]] = sentinel,
) -> Iterator[None]:
    reset_token = context_var.set(context_var.get().set(deadline=deadline, priority=priority))
    try:
        yield
    finally:
        context_var.reset(reset_token)


def get_context() -> Context:
    return context_var.get()

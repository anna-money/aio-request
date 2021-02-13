import contextlib
import contextvars
import dataclasses
from typing import Iterator, Optional, Union, cast

from .deadline import Deadline
from .priority import Priority

sentinel = object()


@dataclasses.dataclass(frozen=True)
class Context:
    __slots__ = ("deadline", "priority")

    deadline: Optional[Deadline]
    priority: Optional[Priority]

    def set(
        self,
        deadline: Optional[Union[Deadline, object]] = sentinel,
        priority: Optional[Union[Priority, object]] = sentinel,
    ) -> "Context":
        return Context(
            deadline=self.deadline if deadline is sentinel else cast(Optional[Deadline], deadline),
            priority=self.priority if priority is sentinel else cast(Optional[Priority], priority),
        )


context_var = contextvars.ContextVar("aio_request_context", default=Context(None, None))


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

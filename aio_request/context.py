import collections.abc
import contextlib
import contextvars
import dataclasses

from .deadline import Deadline
from .priority import Priority

sentinel = object()


@dataclasses.dataclass(frozen=True, slots=True, kw_only=True)
class Context:
    deadline: Deadline | None = None
    priority: Priority | None = None

    def set(
        self,
        deadline: Deadline | object | None = sentinel,
        priority: Priority | object | None = sentinel,
    ) -> "Context":
        return Context(
            deadline=self.deadline if deadline is sentinel else deadline,  # type: ignore
            priority=self.priority if priority is sentinel else priority,  # type: ignore
        )

    def __repr__(self) -> str:
        return f"<Context [{self.deadline} {self.priority}]>"


context_var = contextvars.ContextVar("aio_request_context", default=Context())


@contextlib.contextmanager
def set_context(
    *,
    deadline: Deadline | object | None = sentinel,
    priority: Deadline | object | None = sentinel,
) -> collections.abc.Iterator[None]:
    reset_token = context_var.set(context_var.get().set(deadline=deadline, priority=priority))
    try:
        yield
    finally:
        context_var.reset(reset_token)


def get_context() -> Context:
    return context_var.get()

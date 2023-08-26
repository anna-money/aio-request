import collections.abc
import contextlib
import contextvars
import dataclasses

from .deadline import Deadline
from .priority import Priority


class UseClientDefault:
    __slots__ = ()


USE_CLIENT_DEFAULT = UseClientDefault()


@dataclasses.dataclass(frozen=True, slots=True, kw_only=True)
class Context:
    deadline: Deadline | None = None
    priority: Priority | None = None

    def set(
        self,
        deadline: Deadline | UseClientDefault | None = USE_CLIENT_DEFAULT,
        priority: Priority | UseClientDefault | None = USE_CLIENT_DEFAULT,
    ) -> "Context":
        return Context(
            deadline=self.deadline if isinstance(deadline, UseClientDefault) else deadline,
            priority=self.priority if isinstance(priority, UseClientDefault) else priority,
        )

    def __repr__(self) -> str:
        return f"<Context [{self.deadline} {self.priority}]>"


context_var = contextvars.ContextVar("aio_request_context", default=Context())


@contextlib.contextmanager
def set_context(
    *,
    deadline: Deadline | UseClientDefault | None = USE_CLIENT_DEFAULT,
    priority: Priority | UseClientDefault | None = USE_CLIENT_DEFAULT,
) -> collections.abc.Iterator[None]:
    reset_token = context_var.set(context_var.get().set(deadline=deadline, priority=priority))
    try:
        yield
    finally:
        context_var.reset(reset_token)


def get_context() -> Context:
    return context_var.get()

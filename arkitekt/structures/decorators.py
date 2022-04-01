from typing import Awaitable, Callable, Type, TypeVar

T = TypeVar("T")


async def idshrinker(self):
    return self.id


def wraps(
    identifier: str,
    expander: Callable[[Type[T]], Awaitable[T]],
    shrinker: Callable[[Type[T]], Awaitable[T]] = idshrinker,
) -> Callable[[Type], Type]:
    def real_cls_decorator(cls: Type[T]) -> Type[T]:
        assert isinstance(cls, Type), "This is a class decorator"

        cls.get_identifier = identifier
        cls.ashrink = shrinker
        cls.aexpand = expander

        return cls

    return real_cls_decorator

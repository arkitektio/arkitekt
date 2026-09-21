"""Small extension to tqdm that reports progress to the task it is handed."""

from typing import Any, Iterable, Mapping, TypeVar
from tqdm import tqdm as _tqdm
from rekuest.task import Task

T = TypeVar("T")


class tqdm(_tqdm[T]):
    """A tqdm that reports its progress to ``task``, and so to the Arkitekt UI.

        def segment(images: list[Image], task: Task) -> ...:
            for image in tqdm(images, task=task):
                ...

    Without a task it is a plain tqdm.
    """

    def __init__(
        self,
        iterable: Iterable[T],
        task: Task | None = None,
        desc: str | None = None,
        total: float | None = None,
        leave: bool | None = True,
        file: Any | None = None,
        ncols: int | None = None,
        mininterval: float = 0.1,
        maxinterval: float = 10.0,
        miniters: float | None = None,
        ascii: bool | str | None = None,
        disable: bool | None = False,
        unit: str = "it",
        unit_scale: bool | float = False,
        dynamic_ncols: bool = False,
        smoothing: float = 0.3,
        bar_format: str | None = None,
        initial: float = 0,
        position: int | None = None,
        postfix: Mapping[str, object] | str | None = None,
        unit_divisor: float = 1000,
        write_bytes: bool = False,
        lock_args: tuple[bool | None, float | None] | tuple[bool | None] | None = None,
        nrows: int | None = None,
        colour: str | None = None,
        delay: float | None = 0,
        gui: bool = False,
    ) -> None:
        """The tqdm constructor"""
        super().__init__(
            iterable,
            desc=desc,
            total=total,
            leave=leave,
            file=file,
            ncols=ncols,
            mininterval=mininterval,
            maxinterval=maxinterval,
            miniters=miniters,
            ascii=ascii,
            disable=disable,
            unit=unit,
            unit_scale=unit_scale,
            dynamic_ncols=dynamic_ncols,
            smoothing=smoothing,
            bar_format=bar_format,
            initial=initial,
            position=position,
            postfix=postfix,
            unit_divisor=unit_divisor,
            write_bytes=write_bytes,
            lock_args=lock_args,
            nrows=nrows,
            colour=colour,
            delay=delay,
            gui=gui,
        )

        self._task = task

        self.last_arkitekt_perc = 0

    def update(self, *args: Any, **kwargs: Any):
        """An update method that also reports progress to the task, if one was given

        Returns
        -------
        The return value of tqdm.update
        """
        z = super().update(*args, **kwargs)

        if self._task is not None and self.total:
            if self.last_arkitekt_perc + 0.05 < self.last_print_n / self.total:
                self.last_arkitekt_perc = self.last_print_n / self.total
                self._task.progress(int(self.last_arkitekt_perc * 100))

        return z

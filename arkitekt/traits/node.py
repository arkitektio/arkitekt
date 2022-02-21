from typing import Any
from rich.table import Table

from koil.loop import koil, koil_gen


class Reserve:
    async def call_async_func(self, *args, reserve_params={}, **kwargs):
        async with self.reserve(**reserve_params) as res:
            return await res.assign_async(*args, **kwargs)

    async def call_async_gen(self, *args, reserve_params={}, **kwargs):
        async with self.reserve(**reserve_params) as res:
            async for result in res.stream_async(*args, **kwargs):
                yield result

    def __call__(self, *args: Any, fill_graphical=True, **kwargs) -> Any:
        """Call

        Call is a convenience on max function, its reserves the Node and wraps it either as
        an geneator (both async and non async depending on context) or call it as a function
        this should only be done if you know what you are doing.

        Args:
            reserve_params (dict, optional): [description]. Defaults to {}.

        Returns:
            Any: Generator or Function
        """
        from arkitekt.api.schema import NodeType  # TODO: FIX ciruclar input

        if self.type == NodeType.FUNCTION:
            return koil(self.call_async_func(*args, **kwargs))

        if self.type == NodeType.GENERATOR:
            return koil_gen(self.call_async_gen(*args, **kwargs))

    def __rich_repr__(self):
        yield self.name
        yield "args", self.args
        yield "kwargs", self.kwargs
        yield "returns", self.returns

    def __rich__(self):
        my_table = Table(title=f"Node: {self.name}", show_header=False)

        my_table.add_row("ID", str(self.id))
        my_table.add_row("Package", self.package)
        my_table.add_row("Interface", self.interface)
        my_table.add_row("Type", self.type)

        return my_table

    def _repr_html_(self):
        return f"""
        <div class="container" style="border:1px solid #00000f;padding: 4px;">
            <div class="item item-1 font-xl">{self.name}</div>
            <div class="item item-2">{self.package}/{self.interface}</div>
            <div class="item item-3">Args: {" ".join([port._repr_html_list() for port in self.args])}</div>
            <div class="item item-3">Kwargs: {" ".join([port.key for port in self.kwargs])}</div>
            <div class="item item-3">Returns: {" ".join([port.key for port in self.returns])}</div>
        </div>"""

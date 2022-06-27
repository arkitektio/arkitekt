from pydantic import BaseModel


class Reserve(BaseModel):
    def get_node_type(self):
        return getattr(self, "type")

    async def call_async_func(self, *args, reserve_params={}, **kwargs):
        async with self.reserve(**reserve_params) as res:
            return await res.assign_async(*args, **kwargs)

    async def call_async_gen(self, *args, reserve_params={}, **kwargs):
        async with self.reserve(**reserve_params) as res:
            async for result in res.stream_async(*args, **kwargs):
                yield result

    def __rich_repr__(self):
        yield self.name
        yield "args", self.args
        yield "kwargs", self.kwargs
        yield "returns", self.returns

    def __rich__(self):

        from rich.table import Table

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

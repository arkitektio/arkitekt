from typing import List
from arkitekt.api.schema import (
    ArgPortFragmentBase,
    BoolKwargPortFragment,
    KwargPortFragmentBase,
    ListArgPortFragment,
    ListKwargPortFragment,
    ListReturnPortFragment,
    ListReturnPortFragmentChildStructureReturnPortFragment,
    NodeFragment,
    ReturnPortFragmentBase,
    StringReturnPortFragment,
    StructureArgPortFragment,
    StructureReturnPortFragment,
    find,
)
from fakts import Fakts
from black import format_str, FileMode
import ast
import re


def clean(varStr):
    return re.sub("\W|^(?=\d)", "_", varStr)


identifier_class_map = {
    "representation": "mikro.Representation",
    "omerofile": "mikro.OmeroFile",
    "sample": "mikro.Sample",
    "imageplus": "mikro.ImagePlus",
    "metric": "mikro.Metric",
    "thumbnail": "mikro.Thumbnail",
}

shrinker_map = {
    "representation": "Representation",
    "omerofile": "OmeroFile",
    "sample": "Sample",
    "imageplus": "ImagePlus",
    "metric": "Metric",
    "thumbnail": "Thumbnail",
}

expander_map = shrinker_map


def generate_imports():

    imports = []

    for key, item in identifier_class_map.items():
        imports.append(
            ast.ImportFrom(
                module=".".join(item.split(".")[:-1]),
                names=[ast.alias(name=item.split(".")[-1])],
                level=0,
            )
        )

    imports += [
        ast.ImportFrom(
            module="enum",
            names=[ast.alias(name="Enum")],
            level=0,
        ),
        ast.ImportFrom(
            module="pydantic.fields",
            names=[ast.alias(name="Field")],
            level=0,
        ),
        ast.ImportFrom(
            module="typing",
            names=[
                ast.alias(name="Optional"),
                ast.alias(name="List"),
                ast.alias(name="Dict"),
                ast.alias(name="Union"),
                ast.alias(name="Literal"),
            ],
            level=0,
        ),
    ]

    return imports


def generate_node_args(
    args: List[ArgPortFragmentBase], kwargs: List[KwargPortFragmentBase]
):

    pos_args = []

    for arg in args:
        if isinstance(arg, StructureArgPortFragment):
            pos_args.append(
                ast.arg(
                    arg=arg.key or "fail",
                    annotation=ast.Name(
                        id=shrinker_map[arg.identifier],
                        ctx=ast.Load(),
                    ),
                )
            )

        if isinstance(arg, ListArgPortFragment):
            pos_args.append(
                ast.arg(
                    arg=arg.key or "fail",
                    annotation=ast.Subscript(
                        value=ast.Name("List", ctx=ast.Load()),
                        slice=ast.Name(
                            id=shrinker_map[arg.child.identifier],
                            ctx=ast.Load(),
                        ),
                    ),
                )
            )

    kw_args = []
    kw_values = []

    for kwarg in kwargs:
        if isinstance(kwarg, BoolKwargPortFragment):
            kw_args.append(
                ast.arg(
                    arg=kwarg.key or "fail",
                    annotation=ast.Name(
                        id="bool",
                        ctx=ast.Load(),
                    ),
                )
            )
            kw_values.append(ast.Constant(value=kwarg.defaultBool))

        if isinstance(kwarg, ListKwargPortFragment):
            kw_args.append(
                ast.arg(
                    arg=kwarg.key or "fail",
                    annotation=ast.Subscript(
                        value=ast.Name("List", ctx=ast.Load()),
                        slice=ast.Name(
                            id=shrinker_map[kwarg.child.identifier],
                            ctx=ast.Load(),
                        ),
                    ),
                )
            )
            kw_values.append(ast.Constant(value=None))

    return ast.arguments(
        args=pos_args + kw_args,
        posonlyargs=[],
        kwonlyargs=[],
        kw_defaults=[],
        defaults=kw_values,
    )


def generate_node_returns(returns: List[ReturnPortFragmentBase]):

    if len(returns) == 0:
        return ast.Name(id="None")

    if len(returns) == 1:
        re = returns[0]
        if isinstance(re, StringReturnPortFragment):
            return ast.Name(id="str", ctx=ast.Load())
        if isinstance(re, StructureReturnPortFragment):
            return ast.Name(id=expander_map[re.identifier], ctx=ast.Load())
        if isinstance(re, ListReturnPortFragment):

            if isinstance(
                re.child, ListReturnPortFragmentChildStructureReturnPortFragment
            ):
                return ast.Subscript(
                    value=ast.Name("List", ctx=ast.Load()),
                    slice=ast.Name(
                        id=shrinker_map[re.child.identifier],
                        ctx=ast.Load(),
                    ),
                )
        else:
            return ast.Name(id="ss", ctx=ast.Load())

    tuple_back = []

    return ast.Name(id="xxx", ctx=ast.Load())


def generate_node_doc(node: NodeFragment):

    description = f"{node.name}\n\n{node.description}\n"

    if len(node.args) > 0 or len(node.kwargs) > 0:
        description += "\nArguments:\n"
        for arg in node.args:
            description += f"\t{arg.key} ({arg.typename}) {arg.description}\n"
        for kwarg in node.kwargs:
            description += (
                f"\t{kwarg.key} ({kwarg.typename}, Optional) {kwarg.description}\n"
            )

    if len(node.returns) > 0:
        description += "\nReturns:\n"
        for re in node.returns:
            description += f"\t{re.key} ({re.typename}) {re.description}\n"

    return ast.Expr(value=ast.Constant(value=description))


def node_to_ast(node: NodeFragment):

    return [
        ast.AsyncFunctionDef(
            name=f"{clean(node.interface)}",
            args=generate_node_args(node.args, node.kwargs),
            body=[
                generate_node_doc(node),
                ast.Return(value=ast.Constant(value=None)),
            ],
            decorator_list=[],
            returns=generate_node_returns(node.returns),
        )
    ]


def generate_node_func(
    package: str = "", interface: str = "", file="generated_node.py"
):

    global_tree = []

    global_tree = generate_imports()

    node = find(package=package, interface=interface)

    global_tree += node_to_ast(node)

    md = ast.Module(body=global_tree, type_ignores=[])
    generated = ast.unparse(ast.fix_missing_locations(md))

    res = format_str(generated, mode=FileMode())

    with open(file, "w") as f:
        f.write(res)

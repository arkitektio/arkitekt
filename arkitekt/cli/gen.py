from typing import List
from rekuest.api.schema import (
    NodeFragment,
    ArgPortFragment,
    ChildPortFragment,
    PortKind,
    ReturnPortFragment,
    retrieveall
)
    

from black import format_str, FileMode
import ast
import re
import inflection
from arkitekt import easy

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
    "@mrepresentation": "Representation",
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

def wrap_nullable(arg: ArgPortFragment | ChildPortFragment | ReturnPortFragment, x):
    if arg.nullable:
        return ast.Subscript(
                    value=ast.Name("Optional", ctx=ast.Load()),
                    slice=x,
                )

    return x

def get_arg_annotation(arg: ArgPortFragment | ChildPortFragment | ReturnPortFragment):
    if arg.kind == PortKind.STRUCTURE:
        return wrap_nullable(arg, ast.Name(
                        id = "ID",
                        ctx=ast.Load()))

    if arg.kind == PortKind.INT:
        return wrap_nullable(arg, ast.Name(
                    id="int",
                    ctx=ast.Load(),
                ))
    if arg.kind == PortKind.FLOAT:
        return wrap_nullable(arg, ast.Name(
                    id="float",
                    ctx=ast.Load(),
                ))
    if arg.kind == PortKind.STRING:
        return wrap_nullable(arg, ast.Name(
                    id="str",
                    ctx=ast.Load(),
                ))
    if arg.kind == PortKind.BOOL:
        return wrap_nullable(arg, ast.Name(
                    id="bool",
                    ctx=ast.Load()))
    if arg.kind == PortKind.LIST:
        return wrap_nullable(arg, ast.Subscript(
                    value=ast.Name("List", ctx=ast.Load()),
                    slice=get_arg_annotation(arg.child),
                ))
    if arg.kind == PortKind.DICT:
        return wrap_nullable(arg, ast.Subscript(
                    value=ast.Name("Dict", ctx=ast.Load()),
                    slice=ast.Tuple(elts=[ast.Name("Str", ctx=ast.Load()), get_arg_annotation(arg.child)]),
                ))
    


def generate_node_args(
    args: List[ArgPortFragment]
):

    pos_args = []
    kw_values = []

    for arg in args:
        annotation = get_arg_annotation(arg)
        if arg.default:
            kw_values.append(ast.Constant(value=arg.default))

    return ast.arguments(
        args=pos_args,
        posonlyargs=[],
        kwonlyargs=[],
        kw_defaults=[],
        defaults=kw_values,
    )


def generate_node_returns(returns: List[ReturnPortFragment]):

    if len(returns) == 0:
        return ast.Name(id="None")

    if len(returns) == 1:
        return get_arg_annotation(returns[0])
    
    return ast.Tuple(
        elts=[get_arg_annotation(re) for re in returns],
        ctx=ast.Load(),
    )



def generate_node_doc(node: NodeFragment):

    description = f"{node.name}\n\n{node.description}\n"

    if len(node.args) > 0:
        description += "\nArguments:\n"
        for arg in node.args:
            description += f"\t{arg.key} ({arg.kind}) {arg.description}\n"

    if len(node.returns) > 0:
        description += "\nReturns:\n"
        for re in node.returns:
            description += f"\t{re.key} ({re.kind}) {re.description}\n"

    return ast.Expr(value=ast.Constant(value=description))


def node_to_ast(node: NodeFragment):

    return [
        ast.AsyncFunctionDef(
            name=f"{inflection.underscore(node.name.replace(' ', '_'))}",
            args=generate_node_args(node.args),
            body=[
                generate_node_doc(node),
                ast.Return(value=ast.Constant(value=None)),
            ],
            decorator_list=[],
            returns=generate_node_returns(node.returns),
        )
    ]


def generate_node_func(
    file="generated_node.py"
):

    global_tree = []

    global_tree = generate_imports()

    with easy("nodifier"):
        for node in retrieveall():
            global_tree += node_to_ast(node)

    md = ast.Module(body=global_tree, type_ignores=[])
    generated = ast.unparse(ast.fix_missing_locations(md))

    #res = format_str(generated, mode=FileMode())

    with open(file, "w") as f:
        f.write(generated)


if __name__ == "__main__":
    generate_node_func()




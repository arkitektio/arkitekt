from abc import abstractmethod
import ast
from asyncio import base_events
from typing import List, Optional

from black import os
from turms.config import GeneratorConfig
from graphql.utilities.build_client_schema import GraphQLSchema
from graphql.language.ast import OperationDefinitionNode, OperationType
from turms.globals import FRAGMENT_CLASS_MAP, FRAGMENT_DOCUMENT_MAP
from turms.parser.recurse import recurse_annotation
from turms.plugins.base import Plugin
from pydantic import BaseModel
from graphql.error.graphql_error import GraphQLError
from graphql.error.syntax_error import GraphQLSyntaxError
from graphql.language.ast import (
    DefinitionNode,
    DocumentNode,
    FieldNode,
    FragmentDefinitionNode,
    FragmentSpreadNode,
    InlineFragmentNode,
    ListTypeNode,
    NonNullTypeNode,
    OperationDefinitionNode,
    OperationType,
    SelectionNode,
    SelectionSetNode,
)
from graphql.type.definition import (
    GraphQLEnumType,
    GraphQLField,
    GraphQLInterfaceType,
    GraphQLList,
    GraphQLNonNull,
    GraphQLObjectType,
    GraphQLScalarType,
    GraphQLType,
    get_named_type,
    is_list_type,
)
from graphql.type.validate import get_operation_type_node
from graphql.utilities.build_client_schema import build_client_schema, GraphQLSchema
from graphql.utilities.get_operation_root_type import get_operation_root_type
from graphql.utilities.type_info import TypeInfo, get_field_def

from pydantic.main import BaseModel
from turms.plugins.fragments import generate_fragment
import re
from graphql import language, parse, get_introspection_query, validate
from turms.plugins.funcs import (
    OperationsFuncPlugin,
    OperationsFuncPluginConfig,
    generate_operation_func,
)
from turms.plugins.operation import OperationsPluginConfig, generate_query
from turms.utils import (
    NoDocumentsFoundError,
    generate_typename_field,
    parse_documents,
    fragment_searcher,
    replace_iteratively,
)
import logging
import glob

logger = logging.getLogger(__name__)


class StructurePluginsConfig(BaseModel):
    query_bases: List[str] = ["turms.types.herre.GraphQLQuery"]
    mutation_bases: List[str] = ["turms.types.herre.GraphQLMutation"]
    structure_bases: List[str] = ["arkitekt.types.GraphQLStructure"]

    fragment_bases: List[str] = ["turms.types.object.GraphQLObject"]
    structure_bases: List[str] = [
        "turms.types.object.GraphQLObject",
        "arkitekt.types.GraphQLStructure",
    ]

    prepend: str = ""
    append: str = ""
    structure_glob: Optional[str]
    out_dir: str = "api/structures"


def generate_fragment_tree(
    f: FragmentDefinitionNode,
    client_schema: GraphQLSchema,
    config: GeneratorConfig,
    plugin_config: StructurePluginsConfig,
    structure_name: str,
):
    tree = []
    fields = []
    type = client_schema.get_type(f.type_condition.name.value)

    name = f"{config.prepend_fragment}{f.name.value}{config.append_fragment}"

    fields += [generate_typename_field(type.name)]

    for field in f.selection_set.selections:

        field_definition = get_field_def(client_schema, type, field)
        assert field_definition, "Couldn't find field definition"

        target = (
            field.alias.value
            if hasattr(field, "alias") and field.alias
            else field.name.value
        )

        fields.append(
            ast.AnnAssign(
                target=ast.Name(target, ctx=ast.Store()),
                annotation=recurse_annotation(
                    field,
                    field_definition.type,
                    client_schema,
                    config,
                    tree,
                    parent_name=target.capitalize(),
                ),
                simple=1,
            )
        )

    FRAGMENT_DOCUMENT_MAP[f.name.value] = language.print_ast(f)
    FRAGMENT_CLASS_MAP[f.name.value] = name

    if f.name.value == structure_name:

        print(f"Generating Structure {structure_name}")
        tree.append(
            ast.ClassDef(
                name,
                bases=[
                    ast.Name(id=base.split(".")[-1], ctx=ast.Load())
                    for base in plugin_config.structure_bases
                ],
                decorator_list=[],
                keywords=[],
                body=fields,
            )
        )

    else:
        tree.append(
            ast.ClassDef(
                name,
                bases=[
                    ast.Name(id=base.split(".")[-1], ctx=ast.Load())
                    for base in plugin_config.fragment_bases
                ],
                decorator_list=[],
                keywords=[],
                body=fields,
            )
        )
    return tree


def generate_structure(
    o: OperationDefinitionNode,
    client_schema: GraphQLSchema,
    config: GeneratorConfig,
    plugin_config: StructurePluginsConfig,
):

    tree = []

    x = get_operation_root_type(client_schema, o)
    query_fields = []
    name = f"{plugin_config.prepend}{o.name.value}{plugin_config.append}"

    for field_node in o.selection_set.selections:

        field_node: FieldNode = field_node
        field_definition = get_field_def(client_schema, x, field_node)
        assert field_definition, "Couldn't find field definition"

        target = (
            field_node.alias.value
            if hasattr(field_node, "alias") and field_node.alias
            else field_node.name.value
        )

        query_fields += [
            ast.AnnAssign(
                target=ast.Name(target, ctx=ast.Store()),
                annotation=recurse_annotation(
                    field_node,
                    field_definition.type,
                    client_schema,
                    config,
                    tree,
                    parent_name=name,
                ),
                simple=1,
            )
        ]

    query_document = language.print_ast(o)
    z = fragment_searcher.findall(query_document)

    merged_document = replace_iteratively(query_document)

    query_fields += [
        ast.ClassDef(
            "Meta",
            bases=[],
            decorator_list=[],
            keywords=[],
            body=[
                ast.Assign(
                    targets=[ast.Name(id="ward", ctx=ast.Store())],
                    value=ast.Constant(value=str("arkitekt")),
                ),
                ast.Assign(
                    targets=[ast.Name(id="document", ctx=ast.Store())],
                    value=ast.Constant(value=merged_document),
                ),
            ],
        )
    ]
    tree.append(
        ast.ClassDef(
            name,
            bases=[
                ast.Name(id=base.split(".")[-1], ctx=ast.Load())
                for base in plugin_config.query_bases
            ],
            decorator_list=[],
            keywords=[],
            body=query_fields,
        )
    )

    return tree


class StructurePlugin(Plugin):
    def __init__(self, config=None, **data):
        self.plugin_config = config or StructurePluginsConfig(**data)

    def generate_imports(
        self, config: GeneratorConfig, client_schema: GraphQLSchema
    ) -> List[ast.AST]:
        imports = []

        all_bases = (
            self.plugin_config.query_bases
            + self.plugin_config.mutation_bases
            + self.plugin_config.structure_bases
        )

        for item in all_bases:
            imports.append(
                ast.ImportFrom(
                    module=".".join(item.split(".")[:-1]),
                    names=[ast.alias(name=item.split(".")[-1])],
                    level=0,
                )
            )

        return imports

    def generate_body(
        self, client_schema: GraphQLSchema, config: GeneratorConfig
    ) -> List[ast.AST]:

        files = glob.glob(self.plugin_config.structure_glob, recursive=True)

        errors: List[GraphQLError] = []

        func_config = OperationsFuncPluginConfig(generate_sync=False, prepend_async="")
        operations_plugin_config = OperationsPluginConfig()

        for file in files:
            with open(file, "r") as f:

                filename = os.path.basename(file).split(".")[0]

                print(f)
                structure_tree = []

                dsl = f.read()

                nodes = parse(dsl)
                errors = validate(client_schema, nodes)

                if len(errors) > 0:
                    raise Exception(errors)

                definitions = nodes.definitions

                fragments = [
                    node
                    for node in definitions
                    if isinstance(node, FragmentDefinitionNode)
                ]

                operations = [
                    node
                    for node in definitions
                    if isinstance(node, OperationDefinitionNode)
                ]

                # first lets find the fragment that is going to be the structure
                expand_ops = [op for op in operations if op.name.value == "__expand__"]
                assert (
                    len(expand_ops) == 1
                ), "There can only be one __expand__ operation"

                expand_op = expand_ops[0]

                structure_name = (
                    expand_op.selection_set.selections[0]
                    .selection_set.selections[0]
                    .name.value
                )

                for fragment in fragments:

                    structure_tree += generate_fragment_tree(
                        fragment,
                        client_schema,
                        config,
                        self.plugin_config,
                        structure_name,
                    )

                for operation in operations:
                    if operation.operation == OperationType.QUERY:
                        structure_tree += generate_query(
                            operation, client_schema, config, operations_plugin_config
                        )

                for operation in operations:
                    structure_tree += generate_operation_func(
                        operation, client_schema, config, func_config
                    )

                md = ast.Module(body=structure_tree, type_ignores=[])
                generated = ast.unparse(ast.fix_missing_locations(md))

                if not os.path.isdir(self.plugin_config.out_dir):
                    os.makedirs(self.plugin_config.out_dir)

                with open(
                    os.path.join(self.plugin_config.out_dir, f"{filename}.py"), "w"
                ) as f:
                    f.write(generated)

        return []

from typing import Annotated, Dict, get_type_hints

from pydantic import BaseModel
from rekuest.definition.define import prepare_definition
from rekuest.structures.default import get_default_structure_registry
from rekuest.api.schema import AnnotationInput


class ValueRange(BaseModel):
    min: int
    max: int


x = get_default_structure_registry()
x.register_annotation_converter(
    ValueRange,
    lambda Annotation: AnnotationInput(
        kind="ValueRange", min=Annotation.min, max=Annotation.max
    ),
)


def foo(
    x: Annotated[int, ValueRange(min=0, max=10)], y: Dict[str, int] = {"x": 45}
) -> float:
    """Foo

    Foo does something

    Args:
        x (Annotated[int, ValueRange, optional): The value x (constrained to be min max). .
        y (_type_, optional): _description_. Defaults to {"x": 45}.

    Returns:
        float: _description_
    """
    return x


print(get_type_hints(foo, include_extras=True))


t = prepare_definition(foo, structure_registry=x)
print(t)

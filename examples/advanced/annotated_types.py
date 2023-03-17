from typing import Annotated, Dict

from annotated_types import Gt
from arkitekt import easy

app = easy("annotated_app_example")

@app.rekuest.register()
def foo(
    x: Annotated[int, Gt(3)], y: Dict[str, int] = {"x": 45}
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

# you can use type annotation that will be stored on the rekuest server,
# which can be used to generate documentation and validate input before sending
# the request on the client side, however you will always need to validate on
# the app side (as the client can be malicious, and you can't trust it)
# annotated_types is a library that provides some useful annotations, and arkitekt
# will automatically validate them for you

if __name__ == "__main__":
    with app:
        app.rekuest.run()
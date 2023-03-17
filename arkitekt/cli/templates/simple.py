from arkitekt import register

@register
def hello_world(hello: str) -> None:
    """Hello World

    Prints hello world

    Args:
        hello (str): The hello world string
    """
    print("Hello world")
from arkitekt import register
import time


@register
def generate_n_string(n: int = 10, timeout: int = 2) -> str:
    """Generate N Strings

    This function generates {{n}} strings with a {{timeout}} ms timeout between each string


    Parameters
    ----------
    n : int, optional
        The number of iterations, by default 10
    timeout : int, optional
        The timeout, by default 2

    Returns
    -------
    str
        A string with Hello {n}
    """
    for i in range(n):
        print(i)
        time.sleep(timeout)
        yield f"Hello {i}"


@register
def append_world(hello: str) -> str:
    """Append World

    This function appends world to the input string

    Parameters
    ----------
    hello : str
        The input string

    Returns
    -------
    str
        {{hello}} World
    """ """"""
    return hello + " World"


@register
def print_string(input: str) -> str:
    """Print String

    This function prints the input string to
    the console

    Parameters
    ----------
    input : str
        The input string

     Returns
    -------
    str
        The printed string
    """
    print(input)
    return input

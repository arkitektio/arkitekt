""" An example of a simple template for Arkitekt"""

import time
from typing import Generator

from arkitekt import App, run

# The version of the app. A release is the commit tagged with it (v1.2.3).
__version__ = __APP_VERSION__

# The app is a declaration: who it is, and what it offers. `arkitekt run` finds it
# in this module (as `app`) and runs it; so does `python app.py`, below.
app = App(__APP_ARGUMENTS__)


@app.action
def generate_n_string(n: int = 10, timeout: int = 2) -> Generator[str, None, None]:
    """Generate N Strings

    This function generates a number of strings, with a timeout between each string


    Parameters
    ----------
    n : int, optional
        The number of iterations, by default 10
    timeout : int, optional
        The seconds to wait before each string, by default 2

    Returns
    -------
    str
        A string with Hello {n}
    """
    for i in range(n):
        print(i)
        time.sleep(timeout)
        yield f"Hello {i}"


@app.action
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
        The input string, with World appended
    """
    return hello + " World"


@app.action
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


if __name__ == "__main__":
    run(app)

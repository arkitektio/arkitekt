import os


def build_relative_dir(*args: str) -> str:
    """Build a relative directory from the given arguments

    This will build a relative directory from the given arguments. It will
    join the arguments together using the os.path.join function and append
    THIS directory to the beginning of the path.

    Parameters
    ----------
    *args : str
        The arguments to join together

    Returns
    -------
    str
        The joined path

    """
    this_dir = os.path.dirname(__file__)
    
    return os.path.join(this_dir, *args)
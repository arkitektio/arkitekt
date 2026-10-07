""" An example of a signal filter template for Arkitekt"""

from typing import List

from arkitekt import App, run

# The version of the app. A release is the commit tagged with it (v1.2.3).
__version__ = __APP_VERSION__

# The app is a declaration: who it is, and what it offers. `arkitekt run` finds it
# in this module (as `app`) and runs it; so does `python app.py`, below.
app = App(__APP_ARGUMENTS__)


@app.action
def moving_average(values: List[float], window: int = 3) -> List[float]:
    """Moving Average

    Smooths a signal with a moving average over a window of samples

    Parameters
    ----------
    values : List[float]
        The signal to smooth
    window : int, optional
        The number of samples to average over, by default 3

    Returns
    -------
    List[float]
        The smoothed signal, as long as the input
    """
    if window < 1:
        raise ValueError("The window needs to be at least 1")
    smoothed = []
    for i in range(len(values)):
        chunk = values[max(0, i - window + 1) : i + 1]
        smoothed.append(sum(chunk) / len(chunk))
    return smoothed


@app.action
def threshold(values: List[float], cutoff: float = 0.5) -> List[float]:
    """Threshold

    Sets every value of a signal below the cutoff to zero

    Parameters
    ----------
    values : List[float]
        The signal to threshold
    cutoff : float, optional
        The smallest value that is kept, by default 0.5

    Returns
    -------
    List[float]
        The thresholded signal
    """
    return [value if value >= cutoff else 0.0 for value in values]


if __name__ == "__main__":
    run(app)

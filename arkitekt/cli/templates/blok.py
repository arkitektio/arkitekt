""" An example of a blok agent for Arkitekt: it analyses images, and shows what it finds in a panel of its own"""

from dataclasses import field
from typing import List, Optional

import numpy as np
import xarray as xr

from arkitekt import App, Task, bsx, run
from mikro import Mikro, mikro_service
from mikro.api.schema import ArrayDataset

# The version of the app. A release is the commit tagged with it (v1.2.3).
__version__ = __APP_VERSION__

# The app is a declaration: who it is, what it offers, and the services it uses.
# `arkitekt run` finds it in this module (as `app`) and runs it; so does
# `python app.py`, below.
app = App(__APP_ARGUMENTS__, services=[mikro_service])

#: How many runs the panel remembers.
HISTORY_LENGTH = 5


# ---------------------------------------------------------------------------
# The analysis: plain numpy, apart from the app. It needs no server, so it is
# tested without one (see tests/).
# ---------------------------------------------------------------------------


def intensity_statistics(pixels: np.ndarray) -> dict:
    """The smallest, largest and mean value of an image, and how far its values spread."""
    return {
        "minimum": float(pixels.min()),
        "maximum": float(pixels.max()),
        "mean": float(pixels.mean()),
        "spread": float(pixels.std()),
    }


def intensity_histogram(pixels: np.ndarray, bins: int = 12) -> List[int]:
    """How the values of an image are distributed: per bin, a share (0-100) of the fullest bin."""
    if bins < 1:
        raise ValueError("A histogram needs at least one bin")
    counts, _ = np.histogram(pixels, bins=bins)
    fullest = counts.max()
    return [int(round(100 * count / fullest)) if fullest else 0 for count in counts]


def otsu_threshold(pixels: np.ndarray, bins: int = 256) -> float:
    """The value that splits an image best into a dark and a bright part (Otsu's method)."""
    counts, edges = np.histogram(pixels, bins=bins)
    if counts.sum() == 0 or pixels.min() == pixels.max():
        return float(pixels.min()) if pixels.size else 0.0
    centers = (edges[:-1] + edges[1:]) / 2
    weight_dark = np.cumsum(counts)
    weight_bright = weight_dark[-1] - weight_dark
    sum_dark = np.cumsum(counts * centers)
    with np.errstate(divide="ignore", invalid="ignore"):
        mean_dark = sum_dark / weight_dark
        mean_bright = (sum_dark[-1] - sum_dark) / weight_bright
        between = weight_dark * weight_bright * (mean_dark - mean_bright) ** 2
    return float(centers[int(np.nanargmax(between))])


def label_objects(mask: np.ndarray) -> np.ndarray:
    """Number the connected bright regions of a (y, x) mask: 0 is background, 1.. are objects.

    Two pixels belong together when they touch at an edge. Labels are spread until
    nothing changes any more, which is slow for a large image and enough for a start:
    `scipy.ndimage.label` does the same, faster.
    """
    mask = np.asarray(mask, dtype=bool)
    labels = np.where(mask, np.arange(1, mask.size + 1).reshape(mask.shape), 0)
    while True:
        padded = np.pad(labels, 1)
        neighbours = np.stack(
            [labels, padded[:-2, 1:-1], padded[2:, 1:-1], padded[1:-1, :-2], padded[1:-1, 2:]]
        )
        spread = np.where(mask, neighbours.max(axis=0), 0)
        if np.array_equal(spread, labels):
            break
        labels = spread
    _, numbered = np.unique(labels, return_inverse=True)
    return numbered.reshape(mask.shape)


def count_objects(pixels: np.ndarray, threshold: float) -> int:
    """How many connected regions of an image are brighter than a threshold."""
    return int(label_objects(pixels > threshold).max())


def blobs_on_noise(width: int, height: int, objects: int, seed: Optional[int] = None) -> np.ndarray:
    """A (height, width) test image: bright round blobs on a dim, noisy background."""
    if width < 1 or height < 1:
        raise ValueError("An image needs to be at least one pixel wide and high")
    rng = np.random.default_rng(seed)
    y, x = np.mgrid[0:height, 0:width]
    image = rng.random((height, width)) * 0.2
    radius = max(2.0, min(width, height) / 16)
    for _ in range(objects):
        center_y, center_x = rng.uniform(0, height), rng.uniform(0, width)
        image += np.exp(-((y - center_y) ** 2 + (x - center_x) ** 2) / (2 * radius**2))
    return image


def pixels_of(image: ArrayDataset) -> np.ndarray:
    """The pixels of a stored image, which has to be of two dimensions."""
    pixels = image.data.squeeze().compute().values
    if pixels.ndim != 2:
        raise ValueError(f"Only an image of two dimensions can be analysed, and this one has {pixels.ndim}")
    return pixels


# ---------------------------------------------------------------------------
# The state: what the panel shows. Whoever watches it sees every change as it
# is made; nobody has to ask.
# ---------------------------------------------------------------------------


@app.state
class Analysis:
    """What the agent is doing, and what it found in the last image."""

    status: str = "Idle"
    busy: bool = False
    progress: int = 0
    image_name: str = "No image yet"
    minimum: float = 0.0
    maximum: float = 0.0
    mean: float = 0.0
    spread: float = 0.0
    threshold: float = 0.0
    objects: int = 0
    histogram: List[int] = field(default_factory=list)
    history: List[str] = field(default_factory=list)
    analysed: int = 0


@app.startup
def start_with_nothing_analysed() -> Analysis:
    """The state the app starts with: nothing analysed yet."""
    return Analysis()


def step(state: Analysis, task: Task, progress: int, status: str) -> None:
    """Say how far a run is: to the panel (the state) and to the caller (the task)."""
    state.progress = progress
    state.status = status
    task.progress(progress, status)


# ---------------------------------------------------------------------------
# The actions: what others call, the panel's buttons among them. Each takes the
# state by its class and writes what it does; assigning a field publishes it.
# ---------------------------------------------------------------------------


@app.action
def generate_test_image(
    mikro: Mikro,
    state: Analysis,
    task: Task,
    objects: int = 12,
    size: int = 256,
) -> ArrayDataset:
    """Generate Test Image

    Makes an image of bright blobs on a noisy background, to have something to analyse

    Parameters
    ----------
    objects : int, optional
        How many blobs are placed, by default 12
    size : int, optional
        How many pixels wide and high the image is, by default 256

    Returns
    -------
    ArrayDataset
        The test image
    """
    state.busy = True
    try:
        step(state, task, 20, "Drawing blobs")
        pixels = xr.DataArray(blobs_on_noise(size, size, objects), dims=("y", "x"))
        step(state, task, 70, "Storing the image")
        image = mikro.create_array_dataset(data=pixels, scales=[], name=f"Test image of {objects} blobs", axes=["y", "x"])
        step(state, task, 100, "Idle")
        return image
    finally:
        state.busy = False


@app.action
def analyse_image(image: ArrayDataset, state: Analysis, task: Task, bins: int = 12) -> int:
    """Analyse Image

    Measures the intensities of an image and counts the objects in it

    Parameters
    ----------
    image : ArrayDataset
        The image to analyse, of two dimensions
    bins : int, optional
        How many bins the histogram has, by default 12

    Returns
    -------
    int
        How many objects were found
    """
    state.busy = True
    try:
        step(state, task, 10, "Loading the image")
        pixels = pixels_of(image)
        state.image_name = image.name

        step(state, task, 35, "Measuring intensities")
        statistics = intensity_statistics(pixels)
        # Rounded, as the panel shows them as they are.
        state.minimum, state.maximum = round(statistics["minimum"], 3), round(statistics["maximum"], 3)
        state.mean, state.spread = round(statistics["mean"], 3), round(statistics["spread"], 3)
        state.histogram = intensity_histogram(pixels, bins)

        step(state, task, 60, "Finding the threshold")
        threshold = otsu_threshold(pixels)
        state.threshold = round(threshold, 3)

        step(state, task, 80, "Counting objects")
        state.objects = count_objects(pixels, threshold)

        state.analysed += 1
        state.history = [f"{image.name}: {state.objects} objects", *state.history][:HISTORY_LENGTH]
        step(state, task, 100, "Idle")
        return state.objects
    finally:
        state.busy = False


@app.action
def segment_image(
    image: ArrayDataset,
    mikro: Mikro,
    state: Analysis,
    task: Task,
) -> ArrayDataset:
    """Segment Image

    Stores a labelled image: every object of the image, numbered

    Parameters
    ----------
    image : ArrayDataset
        The image to segment, of two dimensions

    Returns
    -------
    ArrayDataset
        The objects of the image: 0 is background, each object has a number of its own
    """
    state.busy = True
    try:
        step(state, task, 15, "Loading the image")
        pixels = pixels_of(image)
        step(state, task, 40, "Labelling objects")
        labels = label_objects(pixels > otsu_threshold(pixels))
        state.objects = int(labels.max())
        step(state, task, 75, "Storing the objects")
        stored = mikro.create_array_dataset(
            data=xr.DataArray(labels.astype("uint16"), dims=("y", "x")),
            scales=[],
            name=f"Objects of {image.name}",
            axes=["y", "x"],
        )
        step(state, task, 100, "Idle")
        return stored
    finally:
        state.busy = False


@app.action
def clear_history(state: Analysis) -> None:
    """Clear History

    Forgets the runs the panel lists
    """
    state.history = []
    state.analysed = 0


# ---------------------------------------------------------------------------
# The blok: the agent's own panel. A tree of components the user interface
# draws; it reads the state (`@self.Analysis...`), keeps the values of its
# controls for itself (`form`), and its buttons call the actions above.
# `.into(name)` keeps a call at hand: `name.running`, `name.result`.
#
# The components and their props are the ones the Orkestrator app renders. They
# are checked right here, when the blok is declared: one it does not have is
# refused, so a typo fails the tests and not the user interface.
# ---------------------------------------------------------------------------

app.blok(
    "analysis",
    bsx("""
        <Card className="w-[420px] shadow-md">
            <CardHeader>
                <div className="flex items-center justify-between">
                    <CardTitle text="Image analysis" />
                    <Badge text="@self.Analysis.status" />
                </div>
                <CardDescription text="@self.Analysis.image_name" />
            </CardHeader>
            <CardContent className="grid gap-4">
                <Progress value="@self.Analysis.progress" />

                <div className="grid grid-cols-3 gap-2">
                    <div className="rounded-md border p-3">
                        <span className="text-xs text-muted-foreground" text="Objects" />
                        <span className="block text-2xl font-bold" text="@self.Analysis.objects" />
                    </div>
                    <div className="rounded-md border p-3">
                        <span className="text-xs text-muted-foreground" text="Mean" />
                        <span className="block text-2xl font-bold" text="@self.Analysis.mean" />
                    </div>
                    <div className="rounded-md border p-3">
                        <span className="text-xs text-muted-foreground" text="Threshold" />
                        <span className="block text-2xl font-bold" text="@self.Analysis.threshold" />
                    </div>
                </div>

                <div className="grid gap-1">
                    <span className="text-xs text-muted-foreground" text="Intensities" />
                    <foreach items="@self.Analysis.histogram" let="#bin">
                        <Progress className="h-1" value="@bin" />
                    </foreach>
                </div>

                <Separator />

                <div className="grid gap-2">
                    <span className="text-xs text-muted-foreground" text="Blobs in a test image" />
                    <Slider bind="form.objects" min="1" max="40" step="1" />
                    <Button
                        label="Generate a test image"
                        onClick="@self.generate_test_image(objects=form.objects).into(generated)"
                        disabled="@self.Analysis.busy"
                    />
                    <Button
                        label="Analyse it"
                        onClick="@self.analyse_image(image=generated.result).into(analysed)"
                        disabled="@utils.eq(generated.done, False)"
                    />
                    <Button
                        label="Store its objects"
                        variant="outline"
                        onClick="@self.segment_image(image=generated.result).into(segmented)"
                        disabled="@utils.eq(generated.done, False)"
                    />
                </div>

                <Separator />

                <div className="grid gap-1">
                    <div className="flex items-center justify-between">
                        <span className="text-xs text-muted-foreground" text="Last runs" />
                        <Button label="Clear" variant="ghost" onClick="@self.clear_history()" />
                    </div>
                    <foreach items="@self.Analysis.history" let="#entry">
                        <span className="text-sm" text="@entry" />
                    </foreach>
                </div>
            </CardContent>
        </Card>
    """),
    description="What the agent is analysing, what it found, and buttons to run it",
    local_state={"form": {"objects": 12}},
)


if __name__ == "__main__":
    run(app)

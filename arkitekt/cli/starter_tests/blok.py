"""The agent for itself, with no server.

The analysis is tested as the plain functions it is, the panel as the
declaration it is, and what an action writes to the state by calling it with a
state of the test's own. Run these with `uv run pytest`; the release workflow
does too.

The actions that store images need the service: those tests are in
`test___ENTRYPOINT___hub.py`.
"""

from dataclasses import dataclass

import numpy as np
import pytest
import xarray as xr
from arkitekt.runtime import Runtime

from __ENTRYPOINT__ import (
    HISTORY_LENGTH,
    Analysis,
    analyse_image,
    app,
    blobs_on_noise,
    count_objects,
    intensity_histogram,
    intensity_statistics,
    label_objects,
    otsu_threshold,
)

# -- the analysis -----------------------------------------------------------------


def test_statistics_of_an_image():
    statistics = intensity_statistics(np.array([[0.0, 1.0], [2.0, 5.0]]))

    assert statistics["minimum"] == 0.0 and statistics["maximum"] == 5.0
    assert statistics["mean"] == 2.0
    assert statistics["spread"] == pytest.approx(1.8708, abs=1e-4)


def test_a_histogram_is_a_share_of_its_fullest_bin():
    assert intensity_histogram(np.array([0.0, 0.0, 0.0, 0.0, 1.0, 1.0]), bins=2) == [100, 50]
    with pytest.raises(ValueError, match="at least one bin"):
        intensity_histogram(np.ones((2, 2)), bins=0)


def test_the_threshold_lies_between_the_dark_and_the_bright():
    pixels = np.concatenate([np.full(50, 0.1), np.full(50, 0.9)]).reshape(10, 10)

    assert 0.1 < otsu_threshold(pixels) < 0.9


def test_a_flat_image_has_no_threshold_to_find():
    assert otsu_threshold(np.full((4, 4), 0.5)) == 0.5


def test_objects_that_touch_at_an_edge_are_one():
    mask = np.array(
        [
            [1, 1, 0, 0, 1],
            [0, 1, 0, 0, 0],
            [0, 0, 0, 1, 0],
            [1, 0, 0, 1, 1],
        ],
        dtype=bool,
    )

    labels = label_objects(mask)

    assert labels.max() == 4
    assert (labels == 0).sum() == (~mask).sum()
    # Every pixel of the L in the corner carries the same number.
    assert len({labels[0, 0], labels[0, 1], labels[1, 1]}) == 1


def test_nothing_bright_is_no_object():
    assert count_objects(np.zeros((5, 5)), threshold=0.5) == 0


def test_the_blobs_of_a_test_image_are_found_again():
    # Far apart and seeded, so none of them touch.
    pixels = np.zeros((40, 40))
    for y, x in [(8, 8), (8, 30), (30, 8), (30, 30)]:
        pixels[y - 2 : y + 3, x - 2 : x + 3] = 1.0

    assert count_objects(pixels, otsu_threshold(pixels)) == 4


def test_a_test_image_has_the_size_asked_for_and_is_the_same_for_a_seed():
    image = blobs_on_noise(width=32, height=16, objects=3, seed=1)

    assert image.shape == (16, 32)
    assert np.array_equal(image, blobs_on_noise(32, 16, 3, seed=1))
    with pytest.raises(ValueError, match="at least one pixel"):
        blobs_on_noise(0, 16, 3)


# -- what an action writes to the state ---------------------------------------------


@dataclass
class StoredImage:
    """What an action needs of an image, without a service to store one in."""

    name: str
    data: xr.DataArray


class SilentTask:
    """A task nobody listens to; it keeps what it was told."""

    def __init__(self) -> None:
        self.reported: list[tuple[int, str]] = []

    def progress(self, percentage: int, message: str | None = None) -> None:
        self.reported.append((percentage, message or ""))


def four_squares() -> StoredImage:
    pixels = np.zeros((40, 40))
    for y, x in [(8, 8), (8, 30), (30, 8), (30, 30)]:
        pixels[y - 2 : y + 3, x - 2 : x + 3] = 1.0
    return StoredImage("squares", xr.DataArray(pixels, dims=("y", "x")))


def test_analysing_an_image_writes_what_it_found_to_the_state():
    state, task = Analysis(), SilentTask()

    found = analyse_image(four_squares(), state, task, bins=4)

    assert found == 4 and state.objects == 4
    assert state.image_name == "squares"
    assert (state.minimum, state.maximum) == (0.0, 1.0)
    assert len(state.histogram) == 4 and max(state.histogram) == 100
    assert state.history == ["squares: 4 objects"] and state.analysed == 1
    # It ends where it started: not busy, and says so.
    assert (state.busy, state.status, state.progress) == (False, "Idle", 100)
    # The caller heard of every step, in order.
    assert [percentage for percentage, _ in task.reported] == sorted(p for p, _ in task.reported)
    assert task.reported[-1] == (100, "Idle")


def test_the_history_keeps_only_the_last_runs():
    state = Analysis()

    for _ in range(HISTORY_LENGTH + 2):
        analyse_image(four_squares(), state, SilentTask())

    assert len(state.history) == HISTORY_LENGTH
    assert state.analysed == HISTORY_LENGTH + 2


def test_an_image_that_cannot_be_analysed_leaves_the_agent_free():
    state = Analysis()
    volume = StoredImage("volume", xr.DataArray(np.zeros((2, 3, 3)), dims=("z", "y", "x")))

    with pytest.raises(ValueError, match="two dimensions"):
        analyse_image(volume, state, SilentTask())

    assert state.busy is False


# -- the app, and its panel -------------------------------------------------------


def test_the_app_starts_with_nothing_analysed(local_runtime: Runtime[None]):
    state = local_runtime.agent.states["Analysis"]

    assert (state.status, state.busy, state.objects, state.history) == ("Idle", False, 0, [])


def test_clearing_the_history_reaches_the_state_the_panel_shows(local_runtime: Runtime[None]):
    state = local_runtime.agent.states["Analysis"]
    state.history, state.analysed = ["an image: 3 objects"], 1

    local_runtime.call_local("clear_history")

    assert (state.history, state.analysed) == ([], 0)


def test_the_panel_is_declared_and_everything_it_names_exists():
    # Building the declaration resolves what the tree reads and calls: a state or
    # an action it names that the app does not have fails here.
    panel = app.registry.get_declared_bloks()["analysis"]

    assert panel.demo_state["form"] == {"objects": 12}
    assert set(panel.demo_state["self"]["Analysis"]) >= {"status", "progress", "objects", "histogram", "history"}
    # One record for each call a button keeps at hand.
    assert {"generated", "analysed", "segmented"} <= set(panel.demo_state)


def test_the_app_offers_its_actions():
    offered = set(app.registry.implementations)

    assert {"generate_test_image", "analyse_image", "segment_image", "clear_history"} <= offered

from tqdm import tqdm as _tqdm
from rekuest.actors.vars import current_assignation_helper


class tqdm(_tqdm):
    """A tqdm that reports progress to arkitekt through the
    assignation context

    This tqdm assigns the current progress to the current assignation helper
    if it exists. This allows the progress to be reported to the user
    through the Arkitekt UI.

    TODO: Check if this works with the current and next versions of tqdm. Maybe
    we should factor this out into the rekuest package

    """

    def __init__(self, *args, **kwargs) -> None:
        """The tqdm constructor"""
        super().__init__(*args, **kwargs)

        self._assignationhelper = current_assignation_helper.get(None)

        self.last_arkitekt_perc = 0

    def update(self, *args, **kwargs):
        """An update method that reports progress to arkitekt through the
        assignation context and the current assignation helper

        Returns
        -------
        The return value of tqdm.update
        """
        z = super().update(*args, **kwargs)
        if self._assignationhelper:
            if self.last_arkitekt_perc + 0.05 < self.last_print_n / self.total:
                self.last_arkitekt_perc = self.last_print_n / self.total
                self._assignationhelper.progress(int(self.last_arkitekt_perc * 100))

        return z

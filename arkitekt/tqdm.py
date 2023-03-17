from tqdm import tqdm
from rekuest.actors.vars import current_assignation_helper


class tqdm(tqdm):
    """A tqdm that reports progress to arkitekt through the
    assignation contexst"""

    def __init__(self, *args, **kwargs) -> None:
        super().__init__(*args, **kwargs)

        self._assignationhelper = current_assignation_helper.get(None)

        self.last_arkitekt_perc = 0


    def update(self,*args, **kwargs):
        z = super().update(*args, **kwargs)
        if self._assignationhelper:
            if self.last_arkitekt_perc + 0.05 < self.last_print_n / self.total:
                self.last_arkitekt_perc = self.last_print_n / self.total
                self._assignationhelper.progress(int(self.last_arkitekt_perc * 100))

        return z
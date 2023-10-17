from arkitekt import register
import time
from mikro.api.schema import RepresentationFragment, from_xarray


@register
def max_intensity_projection(image: RepresentationFragment) -> RepresentationFragment:
    """Z-Project the Maximum Intensity

    This function projects the maximum intensity of the input image
    along the z-axis

    Parameters
    ----------
    image : RepresentationFragment
        The input image

    Returns
    -------
    RepresentationFragment
        The projected image

    """
    image = image.data.max(dim="z")
    return from_xarray(
        image, name="Max Intensity Projection" + image.name, origins=[image]
    )

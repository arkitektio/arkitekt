from arkitekt_next import register
from mikro_next.api.schema import Image, from_array_like, PartialDerivedViewInput


@register
def max_intensity_projection(image: Image) -> Image:
    """Z-Project the Maximum Intensity

    This function projects the maximum intensity of the input image
    along the z-axis

    Parameters
    ----------
    image : Image
        The input image

    Returns
    -------
    Image
        The projected image

    """
    image_data = image.data.max(dim="z")
    return from_array_like(
        image_data, name="Max Intensity Projection" + image.name, derived_views=[PartialDerivedViewInput(originImage=image)]
    )

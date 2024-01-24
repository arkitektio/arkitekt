"hallo"
from arkitekt.deployed import deployed


composition = deployed("paper", "com.example.test")


@composition.app.rekuest.register()
def test(hallo: str) -> str:
    """Hallo

    Prints hallo

    Args:
        hallo (str): Hallo string

    Returns:
        str: Hallo
    """
    print(hallo)
    return "test"


with composition:

    


    print(composition.deployment.project.compose_files)

    print("hello")

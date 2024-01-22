"hallo"
from arkitekt.deployed import deployed


composition = deployed("paper", "com.example.test")
composition.deployment.up_on_enter = True
composition.deployment.down_on_exit = False
composition.deployment.stop_on_exit = False


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

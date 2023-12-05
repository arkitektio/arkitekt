"hallo"
from arkitekt import easy


print("hello")

app = easy("com.example.test", url="http://localhost:8000", log_level="DEBUG")


@app.rekuest.register()
def test(hallo: str) -> str:
    """Hallo

    Prints hallo

    Args:
        hallo (str): Hallo string

    Returns:
        str: Hallo
    """
    return "test"


with app:
    app.rekuest.run()
    print("hello")

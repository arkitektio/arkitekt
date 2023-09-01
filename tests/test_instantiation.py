from arkitekt.builders import easy


def test_easy():
    with easy("johannes", "latest"):
        print("Hello world!")

"""
 This example shows the two ways to use an app: calling the API from a script,
 and offering an action to others.

 It requires the following packages:
    arkitekt
    mikro

 If you are not concerned about installing multiple packages, you can
  install them with:

 `pip install "arktitekt[all]"`

 To run this example, first start the server, e.g with
 `konstruktor` and then run this script with python3.

"""

from arkitekt import App, easy, run
from mikro import Mikro
from mikro.api.schema import Folder

app = App("upload_test", "0.1.0")
# An app is a declaration: who it is and what it offers. Declaring connects
# nothing, so this line is free.


@app.action
def make_folder(name: str, mikro: Mikro) -> Folder:
    """Create a folder.

    `mikro` is not a port: an app declares the services its actions ask for,
    and the run injects its own client.
    """
    return mikro.create_folder(name=name)


if __name__ == "__main__":
    import sys

    if "--provide" in sys.argv:
        # Offer `make_folder` to others until stopped.
        run(app, url="localhost")
    else:
        # Or just call the API: `easy` declares an app for the script, connects it,
        # and hands back the client, typed. Pass it to the action yourself.
        with easy("upload_test", Mikro, url="localhost") as mikro:
            folder = make_folder("test", mikro=mikro)
            print(folder.id)

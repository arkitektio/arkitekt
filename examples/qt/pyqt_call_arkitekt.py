import sys
from typing import Any
import matplotlib

from matplotlib import pyplot as plt
import numpy as np

from arkitekt_next.qt import qt
from arkitekt_next import find
from PyQt5.QtWidgets import QApplication, QWidget, QPushButton, QVBoxLayout
from mikro_next.api.schema import (
    Image,
)  # important as we are trying to expand the image when receiving it


matplotlib.use("Qt5Agg")


class MainWindow(QWidget):
    def __init__(self):
        super().__init__()
        self.app = qt(
            identifier="com.example.basicqtapp",
            parent=self,
        )

        self.generate_image_worker = self.app.wrap(
            self.generate_random_image
        )  # Wrapping the function puts it in the right thread that arkitekt runs in, and will ensure that before running the users is logged int, within this thread you can call arkitekt functions blockingly

        self.generate_image_worker.returned.connect(
            self.show_image
        )  # this runs again in the main thread if you want to update the UI

        self.init_ui()

    def show_image(self, arr: np.ndarray[Any, Any]) -> None:
        """Display the provided `Image` using matplotlib.

        The `image.data` is typically a dask array; compute it to get a numpy
        array, then show with pyplot. This keeps the existing debug prints.
        """

        # Basic normalization/formatting for display
        try:
            # If it's a single-channel image with a trailing channel axis, squeeze it
            if arr.ndim == 3 and arr.shape[2] == 1:
                arr = arr.squeeze(axis=2)

            cmap = "gray" if arr.ndim == 2 else None
            plt.figure(figsize=(6, 6))
            plt.imshow(arr, cmap=cmap)
            plt.title(f"Image {arr.shape}")
            plt.axis("off")
            plt.show()
        except Exception as e:
            # Keep UI responsive and log errors
            print("Failed to show image with matplotlib:", e)

    def init_ui(self) -> None:
        """ Init the UI components """
        self.setWindowTitle("Basic Qt Application")
        self.setGeometry(300, 300, 300, 200)

        layout = QVBoxLayout()

        self.button = QPushButton("Generate A Random Image", self)
        self.button.clicked.connect(self.on_button_click)

        layout.addWidget(self.button)
        self.setLayout(layout)

    def generate_random_image(self) -> np.ndarray[Any, Any]:
        """Generate a random image using an Arkitekt action
        
        Returns
        -------
        np.ndarray
            The generated image as a numpy array
        """
        action = find(
            "4df8e256536caceb577d35a5766810371f767ed2c434f8dabb82a24f68f8045f"
        )  # finds an arktiekt action by its hash

        image: Image = action(width=200, height=400)  # calls the action blockingly

        arr = image.data.sel(c=0, z=0, t=0).to_numpy()
        return arr

    def on_button_click(self):
        self.generate_image_worker.run()
        print("Button clicked!")


def main():
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    sys.exit(app.exec_())


if __name__ == "__main__":
    main()

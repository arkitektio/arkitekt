import os


IMAGES_PATH = os.path.dirname(os.path.realpath(__file__))

def get_image_path(filename, darkMode=False):
    base_folder =  os.path.join(IMAGES_PATH,"darkmode") if darkMode else os.path.join(IMAGES_PATH, "lightmode") 
    return os.path.join(base_folder,filename)



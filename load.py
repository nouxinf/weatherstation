import os
import glob
import shutil

SOURCE_DIR = "."
APP_PATH = "F:/apps/"
INSTALL_PATH = "weatherstation/"
FILES_TO_TRANSFER = ["__init__.py", "icon.png", "options.json"]
DIRS_TO_TRANSFER = ["assets"]

full_install_path = os.path.join(APP_PATH, INSTALL_PATH)

if os.path.isdir(APP_PATH):
    os.makedirs(full_install_path, exist_ok=True)

    for f in glob.glob(os.path.join(full_install_path, "*")):
        if os.path.isfile(f):
            os.remove(f)
        elif os.path.isdir(f):
            shutil.rmtree(f)

    for filename in FILES_TO_TRANSFER:
        src = os.path.join(SOURCE_DIR, filename)
        dst = os.path.join(full_install_path, filename)
        shutil.copy2(src, dst)

    for dirname in DIRS_TO_TRANSFER:
        src = os.path.join(SOURCE_DIR, dirname)
        dst = os.path.join(full_install_path, dirname)
        shutil.copytree(src, dst, dirs_exist_ok=True)
else:
    print(
        f"Warning: {APP_PATH} does not exist, skipping installation. You probably need to change the directory in APP_PATH"
    )

# this script helps transfer the project files to the tufty

import os, glob, shutil

SOURCE_DIR = "."
INSTALL_PATH = "F:/apps/weatherstation/"
FILES_TO_TRANSFER = ["__init__.py", "icon.png"]

if os.path.isdir(INSTALL_PATH):
    for f in glob.glob(os.path.join(INSTALL_PATH, "*")):
        if os.path.isfile(f):
            os.remove(f)
        elif os.path.isdir(f):
            shutil.rmtree(f)
    for filename in FILES_TO_TRANSFER:
        src = os.path.join(SOURCE_DIR, filename)
        dst = os.path.join(INSTALL_PATH, filename)
        shutil.copy2(src, dst)

else:
    print(f"Warning: {INSTALL_PATH} does not exist, skipping cleanup")

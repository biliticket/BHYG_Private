from distutils.core import setup
from Cython.Build import cythonize

import platform

if platform.system() == "Windows":
    name = "BHYG-Windows"
elif platform.system() == "Linux":
    name = "BHYG-Linux"
elif platform.system() == "Darwin":
    print(platform.machine())
    if "arm" in platform.machine():
        name = "BHYG-macOS-Apple_Silicon"
    elif "64" in platform.machine():
        name = "BHYG-macOS-Intel"
    else:
        name = "BHYG-macOS"
else:
    name = "BHYG"

setup(
    name=name,
    ext_modules=cythonize(
        [
            "api.py",
            "main.py",
            "utility.py",
            "i18n.py",
            "login.py",
            "geetest.py",
            "globals.py",
            "utils.py",
        ]
    ),
)

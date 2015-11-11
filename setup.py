from distutils.core import setup
import py2exe
"""
this should just run by typing python setup.py py2exe from the command line
"""

setup (
    options = {
        "py2exe": {"compressed": 1,
                   "optimize":2,
                   "ascii":1,
                   "bundle_files":1,
                   "packages": "encodings, pubsub",
                   "dll_excludes": ["MSVCP90.dll"]
        }
    },console=['Whouse.py'])

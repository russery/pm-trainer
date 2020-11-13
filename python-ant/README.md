ANT
===

Introduction
------------
Python implementation of the ANT, ANT+, and ANT-FS protocols. For more
information about ANT, see http://www.thisisant.com/.

Can be used to communicate with ANT nodes using an ANT stick (USB).

This is a fork of the original project python-ant project, which can be found here:
https://github.com/mvillalba/python-ant


License
-------
Released under the MIT/X11 license. See LICENSE for the full text.


Install
-------
% python setup.py install


Develop
-------
See DEVELOP.md for details.

A few quick notes for now:

Run unit tests:
```
python -m unittest discover
```

Run pylint:
```
pylint src/ant
```

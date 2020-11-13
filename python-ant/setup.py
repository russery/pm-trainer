# -*- coding: utf-8 -*-
##############################################################################
#
# Copyright (c) 2011, Martín Raúl Villalba
#
# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the "Software"), to
# deal in the Software without restriction, including without limitation the
# rights to use, copy, modify, merge, publish, distribute, sublicense, and/or
# sell copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:
#
# The above copyright notice and this permission notice shall be included in
# all copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING
# FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS
# IN THE SOFTWARE.
#
##############################################################################

import os

from setuptools import setup, find_packages
from unittest import TestLoader

baseDir = os.path.dirname(os.path.abspath(__file__))
os.chdir(baseDir)

def read(fname):
    return open(os.path.join(baseDir, fname)).read()

def test_suite():
    return TestLoader().discover('tests', pattern='test_*.py')

setup(
    name='ant',
    version='0.1.1',
    url='http://www.github.com/mch/python-ant',
    license='MIT',
    description='Python implementation of the ANT, ANT+, and ANT-FS ' \
                'protocols (http://www.thisisant.com/).',
    author=u'Mart\u00EDn Ra\u00FAl Villalba',
    author_email='martin@martinvillalba.com',
    long_description=read('README.md'),
    classifiers=[
        "Development Status :: 2 - Pre-Alpha",
        "Intended Audience :: Developers",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
        "Programming Language :: Python",
        "Programming Language :: Python :: 2.6",
        "Programming Language :: Python :: 2.7",
        "Topic :: Communications",
        "Topic :: Communications :: File Sharing",
        "Topic :: Software Development :: Libraries :: Python Modules",
    ],
    packages=find_packages('src'),
    package_dir={'': 'src'},
    install_requires=[
        'pyserial',
        'pyusb>=1.0.0b2',
        'msgpack-python',
        'six>=1.7.0',
    ],
    test_suite='setup.test_suite'
)

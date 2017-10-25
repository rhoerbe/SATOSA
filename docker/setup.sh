#!/bin/bash
set -e
pip3 install --upgrade virtualenv

virtualenv -p python3 /opt/satosa
/opt/satosa/bin/pip install --upgrade pip setuptools

# Optional code to get fres version of pysaml2 - not required as 4.5.0 has been pushed to pypi
#cd /src
#git clone https://github.com/rohe/pysaml2
#cd pysaml2
#/opt/satosa/bin/python setup.py install

/opt/satosa/bin/pip install /src/satosa/


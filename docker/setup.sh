#!/bin/bash

pip3 install --upgrade virtualenv

virtualenv -p python3 /opt/satosa
/opt/satosa/bin/pip install --upgrade pip setuptools

# pysaml2 4.4.0 not good enough: sigver breaks on diacritic chars in metadata
cd /src
git clone https://github.com/rohe/pysaml2
cd pysaml2
python setup.py install

/opt/satosa/bin/pip install /src/satosa/


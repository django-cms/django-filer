#!/bin/bash
find . -name '*.pyc' -delete
export DJANGO_VERSION="1.3.1"
./.travis_setup
python setup.py test
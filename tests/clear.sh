#!/bin/bash

rm -rvf eggs/
rm -rvf downloads/
rm -rvf develop-eggs/
rm -rvf bin/
rm -rvf parts/
rm -rvf .installed.cfg
rm -rvf .buildoutsig


find . -name '*.pyc' -delete
find . -name '*.pyo' -delete

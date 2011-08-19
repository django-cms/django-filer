#!/bin/bash

rm -rf eggs/
rm -rf downloads/
rm -rf develop-eggs/
rm -rf bin/
rm -rf parts/
rm -rf .installed.cfg
rm -rf .buildoutsig


find . -name '*.pyc' -delete
find . -name '*.pyo' -delete

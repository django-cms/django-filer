#!/bin/bash
read -r -p "This will install dependencies and run the testsuite. Please make sure you are in a virtualenv! Continue? [Y/n]" response
case $response in
	[yY]|[eE]|[sS]|[yY])
		;;
	*)
		echo "cancelled"
		exit
		;;
esac

find . -name '*.pyc' -delete
export DJANGO_VERSION="1.3.1"
./.travis_setup
python setup.py test

#find . -name '*.pyc' -delete
#export DJANGO_VERSION="1.4"
#./.travis_setup
#python setup.py test
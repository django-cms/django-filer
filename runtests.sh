#!/bin/bash

django="13"
args=("$@")
num_args=${#args[@]}
index=0
while [ "$index" -lt "$num_args" ]
do
    case "${args[$index]}" in
        "-d"|"--django")
            let "index = $index + 1"
            django="${args[$index]}"
            ;;

        "-h"|"--help")
            echo ""
            echo "usage:"
            echo "    runtests.sh"
            echo "    or runtests.sh [-d <version>|--django <version>]"
            echo ""
            echo "flags:"
            echo "    -d, --django <version> - run tests against a django version, options: 13 or 14"
            exit 1
            ;;

    esac
    let "index = $index + 1"
done

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

if [ $django == "13" ]; then
    export DJANGO_VERSION="1.3.1"
fi
if [ $django == "14" ]; then
    export DJANGO_VERSION="1.4"
fi

./.travis_setup
python setup.py test

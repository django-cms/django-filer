#!/bin/bash

extra=""
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
            echo "    or runtests.sh [-d <version>|--django <version>] [test arguments]"
            echo ""
            echo "flags:"
            echo "    -d, --django <version> - run tests against a django version, options: 13 or 14"
            echo ""
            echo "test arguments:"
            echo "    any other argument is passed to setup.py test command for further evaluation"
            exit 1
            ;;

        *)
            extra="$extra ${args[$index]}"
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
    export DJANGO="django>=1.3,<1.4"
fi
if [ $django == "14" ]; then
    export DJANGO="django>=1.4,<1.5"
fi
if [ $django == "dev" ]; then
    export DJANGO="-e git+git://github.com/django/django.git#egg=Django"
fi

./.travis_setup
python setup.py test $extra

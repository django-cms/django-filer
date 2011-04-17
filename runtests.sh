#!/bin/bash

args=("$@")
num_args=${#args[@]}
index=0

suite='filer'

coverage=false
documentation=false

while [ "$index" -lt "$num_args" ]
do
        case "${args[$index]}" in
                "--with-docs")
                        documentation=true
                        ;;
                "--with-coverage")
                        coverage=true
                        ;;
                *)
                        suite="shop.${args[$index]}"
        esac
let "index = $index + 1"
done

if [ $coverage == true ]; then
        pushd .
        cd tests/
        coverage run bin/django test $suite
        coverage html
        popd

else

        # the default case...
        pushd .
        cd tests/
        bin/django test $suite
        popd

fi

if [ $documentation == true ]; then
        pushd .
        cd docs/
        make html
        popd
fi


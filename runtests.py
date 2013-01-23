#!/usr/bin/env python
from filer.test_utils.cli import configure
from filer.test_utils.tmpdir import temp_dir
import argparse
import sys
import warnings


def main(verbosity=1, failfast=False, test_labels=None):
    verbosity = int(verbosity)
    if not test_labels:
        test_labels = ['filer']
    with temp_dir() as STATIC_ROOT:
        with temp_dir() as MEDIA_ROOT:
            with temp_dir() as FILE_UPLOAD_TEMP_DIR:
                # from django import VERSION
                # use_tz = VERSION[:2] >= (1, 4)
                use_tz = False
                warnings.filterwarnings(
                    'error', r"DateTimeField received a naive datetime",
                    RuntimeWarning, r'django\.db\.models\.fields')
                configure(
                    ROOT_URLCONF='test_urls',
                    STATIC_ROOT=STATIC_ROOT, MEDIA_ROOT=MEDIA_ROOT,
                    FILE_UPLOAD_TEMP_DIR=FILE_UPLOAD_TEMP_DIR,
                    USE_TZ=use_tz)
                from django.conf import settings
                from django.test.utils import get_runner
                TestRunner = get_runner(settings)
                test_runner = TestRunner(verbosity=verbosity, interactive=False, failfast=failfast)
                failures = test_runner.run_tests(test_labels)
    sys.exit(failures)


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--failfast', action='store_true', default=False, dest='failfast')
    parser.add_argument('--verbosity', default=1)
    parser.add_argument('test_labels', nargs='*')
    args = parser.parse_args()
    test_labels = ['%s' % label for label in args.test_labels]
    main(verbosity=args.verbosity, failfast=args.failfast, test_labels=test_labels)

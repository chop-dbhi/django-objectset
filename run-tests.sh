#!/bin/sh

ARGS="$@"

if [ ! $ARGS ]; then
    ARGS="tests"
fi

DJANGO_SETTINGS_MODULE='tests.settings' PYTHONPATH=. `which django-admin.py` test $ARGS

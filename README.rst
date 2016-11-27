Sentry stack checker
====================

Pylint plugin for finding calls to ``log.exception(extra={'stack': True})``,
which includes the stack from the log statement, where we typically want the
stack from the exception.

Installation
------------

::

    $ pip install sentry_stack_checker

Usage
-----

::

    $ pylint --load-plugins sentry_stack_checker <module> -E -d all -e R9501

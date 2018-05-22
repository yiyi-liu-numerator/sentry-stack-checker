Sentry stack checker
====================

Pylint plugin for finding logging calls inside exception handlers, and suggest they include ``exc_info=True``, or change ``extra={'stack': True}`` to ``exc_info=True`` to get the stack from the exception instead of the one from the log statement.

Installation
------------

::

    $ pip install sentry_stack_checker

Usage
-----

::

    $ pylint --load-plugins sentry_stack_checker <module> -E -d all -e R9501
    $ pylint --load-plugins sentry_stack_checker <module> -E -d all -e R9502

The option ``report-loggers`` can be provided to restrict the logging methods that are checked:

::

    $ pylint --load-plugins sentry_stack_checker <module> --report-loggers=warning,error

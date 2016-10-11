import os.path as osp
import unittest

from pylint import checkers
from pylint.lint import PyLinter
from pylint.reporters import BaseReporter

import pytest

from sentry_stack_checker import SentryStackChecker, register


class TestReporter(BaseReporter):

    def handle_message(self, msg):
        self.messages.append(msg)

    def on_set_current_module(self, module, filepath):
        self.messages = []


@pytest.fixture
def linter():
    linter = PyLinter()
    linter.set_reporter(TestReporter())
    checkers.initialize(linter)
    register(linter)
    linter.disable('all')
    linter.enable(SentryStackChecker.MESSAGE_ID)
    return linter


def test_foo(tmpdir, linter):
    source = tmpdir.join("source.py")
    source.write("""\
import logging
logger = logging.getLogger(__name__)

logger.exception()
logger.exception(extra={'stack': True})
logger.error(extra={'stack': True})

log = logger
log.exception(extra={'stack': True})

class Foo(object):
    def exception(self, *args, **kwargs):
        pass

foo = Foo()
foo.exception(extra={'stack': True})
    """)

    linter.check([str(source)])
    error_lines = [message.line for message in linter.reporter.messages]
    msgs = [message.msg for message in linter.reporter.messages]
    expected_error_lines = [5, 9]
    assert error_lines == expected_error_lines
    assert set(msgs) == set(
        ['logger.exception calls should not pass `stack: True`']
    )

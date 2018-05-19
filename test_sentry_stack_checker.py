import astroid
from astroid.node_classes import Call

from pylint import checkers
from pylint.lint import PyLinter
from pylint.reporters import BaseReporter

import pytest

from sentry_stack_checker import (
    SentryStackChecker, register, includes_extra_stack,
)


class InMemReporter(BaseReporter):

    def handle_message(self, msg):
        self.messages.append(msg)

    def on_set_current_module(self, module, filepath):
        self.messages = []


@pytest.fixture
def linter():
    linter = PyLinter()
    linter.set_reporter(InMemReporter())
    checkers.initialize(linter)
    register(linter)
    linter.disable('all')
    linter.enable(SentryStackChecker.ADD_EXC_INFO)
    linter.enable(SentryStackChecker.CHANGE_TO_EXC_INFO)
    return linter


@pytest.fixture
def make_source(tmpdir):
    def make(source):
        source_file = tmpdir.join("source.py")
        source_file.write("""\
import logging
logger = logging.getLogger(__name__)
""" + source)
        return source_file
    return make


def test_basic_add(make_source, linter):
    source = make_source("""
try:
    pass
except:
    logger.warn('foo')
""")
    linter.check([str(source)])
    errors = [message.symbol for message in linter.reporter.messages]
    assert errors == [SentryStackChecker.ADD_EXC_INFO]


def test_basic_change(make_source, linter):
    source = make_source("""
try:
    pass
except:
    logger.warn('foo', extra=dict(stack=True))
""")
    linter.check([str(source)])
    errors = [message.symbol for message in linter.reporter.messages]
    assert errors == [SentryStackChecker.CHANGE_TO_EXC_INFO]


def test_no_exception(make_source, linter):
    source = make_source("""
logger.warn('foo')
""")
    linter.check([str(source)])
    errors = [message.symbol for message in linter.reporter.messages]
    assert errors == []


def test_log_with_exc_info(make_source, linter):
    source = make_source("""
try:
    pass
except:
    logger.info('foo', exc_info=True)
""")
    linter.check([str(source)])
    errors = [message.symbol for message in linter.reporter.messages]
    assert errors == []


def test_ignore_non_log_calls(make_source, linter):
    source = make_source("""
class Other():
    def info(s, *a, **k):
        pass

try:
    pass
except:
    Other().info('foo')
""")
    linter.check([str(source)])
    errors = [message.symbol for message in linter.reporter.messages]
    assert errors == []


def test_inference_error(make_source, linter):
    source = make_source("""
undefined.info('foo')
""")
    linter.check([str(source)])
    errors = [message.symbol for message in linter.reporter.messages]
    assert errors == []


def test_log_except_implicitly_includes_exc_info(make_source, linter):
    source = make_source("""
try:
    pass
except:
    logger.exception('foo')
""")
    linter.check([str(source)])
    errors = [message.symbol for message in linter.reporter.messages]
    assert errors == []


def find_children(node):
    children = [node]
    for child in children:
        children.extend(list(child.get_children()))
    return children


def find_call(nodes):
    for node in nodes:
        if isinstance(node, Call):
            return node


@pytest.mark.parametrize('source, includes_stack', [
    ("logger.warn('foo')", False),
    ("logger.warn('foo', extra=True)", False),
    ("logger.warn('foo', extra={})", False),
    ("logger.warn('foo', extra={'stack': False})", False),
    ("logger.warn('foo', extra={'other': True})", False),
    ("logger.warn('foo', extra={'stack': True})", True),
    ("logger.warn('foo', extra=dict())", False),
    ("logger.warn('foo', extra=dict(stack=False))", False),
    ("logger.warn('foo', extra=dict(other=True))", False),
    ("logger.warn('foo', extra=dict(stack=True))", True),
])
def test_includes_extra_stack(source, includes_stack):
    module_node = astroid.parse(source)
    call_node = find_call(find_children(module_node))
    assert includes_extra_stack(call_node) == includes_stack

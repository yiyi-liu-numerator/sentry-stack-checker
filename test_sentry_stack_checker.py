import astroid
import pylint.testutils

from astroid.nodes import Call

import pytest

from sentry_stack_checker import (
    SentryStackChecker, includes_extra_stack, register,
)


class TestSentryStackChecker(pylint.testutils.CheckerTestCase):
    CHECKER_CLASS = SentryStackChecker

    def test_register_function(self):
        """Test that the register function works correctly."""
        # Use the actual linter from the test case
        original_checkers_count = len(self.linter._checkers)
        register(self.linter)
        
        # Verify that a new checker was registered
        assert len(self.linter._checkers) > original_checkers_count

    def test_non_reported_logging_method_ignored(self):
        """Test that logging methods not in report_loggers are ignored."""
        # Set up checker with only 'error' in report_loggers
        self.checker.logging_methods_to_report = {'error'}
        
        call_node = astroid.extract_node("""
import logging
logger = logging.getLogger(__name__)
try:
    pass
except:
    logger.debug('foo') #@
""")
        
        # Should not add any messages since 'debug' is not in report_loggers
        with self.assertNoMessages():
            self.checker.visit_call(call_node)

    def test_basic_add_exc_info(self):
        """Test that we suggest adding exc_info=True in exception handlers."""
        call_node = astroid.extract_node("""
import logging
logger = logging.getLogger(__name__)
try:
    pass
except:
    logger.warn('foo') #@
""")
        
        with self.assertAddsMessages(
            pylint.testutils.MessageTest(
                msg_id=SentryStackChecker.ADD_EXC_INFO,
                node=call_node,
            ),
            ignore_position=True,  # Ignore position since it can vary
        ):
            self.checker.visit_call(call_node)

    def test_basic_change_to_exc_info(self):
        """Test that we suggest changing stack=True to exc_info=True."""
        call_node = astroid.extract_node("""
import logging
logger = logging.getLogger(__name__)
try:
    pass
except:
    logger.warn('foo', extra=dict(stack=True)) #@
""")
        
        with self.assertAddsMessages(
            pylint.testutils.MessageTest(
                msg_id=SentryStackChecker.CHANGE_TO_EXC_INFO,
                node=call_node,
            ),
            ignore_position=True,  # Ignore position since it can vary

        ):
            self.checker.visit_call(call_node)

    def test_no_exception_context(self):
        """Test that we don't trigger outside exception handlers."""
        call_node = astroid.extract_node("""
import logging
logger = logging.getLogger(__name__)
logger.warn('foo') #@
""")
        
        with self.assertNoMessages():
            self.checker.visit_call(call_node)

    def test_log_with_exc_info_already_present(self):
        """Test that we don't trigger when exc_info=True is already present."""
        call_node = astroid.extract_node("""
import logging
logger = logging.getLogger(__name__)
try:
    pass
except:
    logger.info('foo', exc_info=True) #@
""")
        
        with self.assertNoMessages():
            self.checker.visit_call(call_node)

    def test_ignore_non_logger_calls(self):
        """Test that we ignore calls to non-logger objects."""
        call_node = astroid.extract_node("""
class Other:
    def info(self, *args, **kwargs):
        pass

try:
    pass
except:
    Other().info('foo') #@
""")
        
        with self.assertNoMessages():
            self.checker.visit_call(call_node)

    def test_exception_method_has_implicit_exc_info(self):
        """Test that logger.exception() doesn't trigger warnings."""
        call_node = astroid.extract_node("""
import logging
logger = logging.getLogger(__name__)
try:
    pass
except:
    logger.exception('foo') #@
""")
        
        with self.assertNoMessages():
            self.checker.visit_call(call_node)

    def test_report_loggers_option_excludes_info(self):
        """Test that info() calls are ignored when not in report-loggers option."""
        # Configure checker to only report warn and error
        self.checker.linter.config.report_loggers = ['warn', 'error']
        self.checker.logging_methods_to_report = {'warn', 'error'}
        
        call_node = astroid.extract_node("""
import logging
logger = logging.getLogger(__name__)
try:
    pass
except:
    logger.info('foo') #@
""")
        
        with self.assertNoMessages():
            self.checker.visit_call(call_node)

    def test_report_loggers_warn_when_warning_specified(self):
        """Test that warn() is reported when warning is in report-loggers."""
        # Configure checker to report warning (which should include warn)
        self.checker.linter.config.report_loggers = ['warning']
        self.checker.logging_methods_to_report = {'warn', 'warning'}
        
        call_node = astroid.extract_node("""
import logging
logger = logging.getLogger(__name__)
try:
    pass
except:
    logger.warn('foo') #@
""")
        
        with self.assertAddsMessages(
            pylint.testutils.MessageTest(
                msg_id=SentryStackChecker.ADD_EXC_INFO,
                node=call_node,
            ),
            ignore_position=True,  # Ignore position since it can vary
        ):
            self.checker.visit_call(call_node)

    def test_inference_error_ignored(self):
        """Test that inference errors are handled gracefully."""
        call_node = astroid.extract_node("""
undefined.info('foo') #@
""")
        
        with self.assertNoMessages():
            self.checker.visit_call(call_node)

    def test_non_method_call_ignored(self):
        """Test that function calls that are not method calls are ignored."""
        call_node = astroid.extract_node("""
import logging
logger = logging.getLogger(__name__)
try:
    pass
except:
    print('foo') #@
""")
        
        # Should not add any messages since print() is not a method call
        with self.assertNoMessages():
            self.checker.visit_call(call_node)



def find_children(node):
    """Helper function to find all child nodes."""
    children = [node]
    for child in children:
        children.extend(list(child.get_children()))
    return children


def find_call(nodes):
    """Helper function to find Call nodes."""
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
    """Test the includes_extra_stack utility function."""
    module_node = astroid.parse(source)
    call_node = find_call(find_children(module_node))
    assert includes_extra_stack(call_node) == includes_stack

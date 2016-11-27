"""Checker for calls to logger.exception with `stack: True`."""

import astroid
from astroid.node_classes import ExceptHandler

from pylint.checkers import BaseChecker, utils
from pylint.interfaces import IAstroidChecker


def register(linter):
    """Register checker."""
    linter.register_checker(SentryStackChecker(linter))


# from pylint/pylint/checkers/logging.py
def is_logger_class(node):
    try:
        for inferred in node.func.infer():
            if isinstance(inferred, astroid.BoundMethod):
                parent = inferred._proxied.parent
                if (
                    isinstance(parent, astroid.ClassDef) and
                    (
                        parent.qname() == 'logging.Logger' or
                        any(
                            ancestor.qname() == 'logging.Logger'
                            for ancestor in parent.ancestors()
                        )
                    )
                ):
                    return True
    except astroid.exceptions.InferenceError:
        pass
    return False


def includes_extra_stack(node):
    try:
        extra = utils.get_argument_from_call(node, keyword='extra')
    except utils.NoSuchArgumentError:
        return False

    if not isinstance(extra, astroid.Dict):
        return False

    for key, value in extra.items:
        if key.value == 'stack' and value.value:
            return True
    return False


def includes_exc_info(node):
    if node.func.attrname == 'exception':
        return True

    try:
        exc_info = utils.get_argument_from_call(node, keyword='exc_info')
    except utils.NoSuchArgumentError:
        return False
    return bool(exc_info.value)


def in_except_handler(node):
    parent = node.parent
    if parent is None:
        return False

    if isinstance(parent, ExceptHandler):
        return True

    return in_except_handler(parent)


class SentryStackChecker(BaseChecker):
    """
    Checks calls to log.exception that include `stack: True` as extra. This
    captures the stack from the logging call, whereas we typically want the
    stack from the most recent exception.  The message id is
    `translation-of-non-string`.
    """

    __implements__ = (IAstroidChecker,)

    name = 'sentry-stack-checker'

    ADD_EXC_INFO = 'exc-log-add-exc-info'
    CHANGE_TO_EXC_INFO = 'exc-log-change-to-exc-info'
    msgs = {
        'R9501': (
            "Consider changing `'stack': True` to `exc_info=True`",
            CHANGE_TO_EXC_INFO,
            None,
        ),
        'R9502': (
            "Consider adding `exc_info=True`",
            ADD_EXC_INFO,
            None,
        ),
    }

    @utils.check_messages(ADD_EXC_INFO, CHANGE_TO_EXC_INFO)
    def visit_callfunc(self, node):
        """Called for every function call in the source code."""

        if not isinstance(node.func, astroid.Attribute):
            # we are looking for method calls
            return

        if node.func.attrname not in [
            'debug',
            'info',
            'warn',
            'warning',
            'error',
            'exception',
        ]:
            return

        if not is_logger_class(node):
            return

        if not in_except_handler(node):
            return

        if includes_exc_info(node):
            return

        if not includes_extra_stack(node):
            self.add_message(self.ADD_EXC_INFO, node=node)
        else:
            self.add_message(self.CHANGE_TO_EXC_INFO, node=node)

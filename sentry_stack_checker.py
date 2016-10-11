"""Checker for calls to logger.exception with `stack: True`."""

import astroid

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


class SentryStackChecker(BaseChecker):
    """
    Checks calls to log.exception that include `stack: True` as extra. This
    captures the stack from the logging call, whereas we typically want the
    stack from the most recent exception.  The message id is
    `translation-of-non-string`.
    """

    __implements__ = (IAstroidChecker,)

    name = 'sentry-stack-checker'

    MESSAGE_ID = 'log-exception-with-stack-true'
    msgs = {
        'W9501': (
            "logger.exception calls should not pass `stack: True`",
            MESSAGE_ID,
            None,
        ),
    }

    @utils.check_messages(MESSAGE_ID)
    def visit_callfunc(self, node):
        """Called for every function call in the source code."""

        if not isinstance(node.func, astroid.Attribute):
            # we are looking for method calls
            return

        if node.func.attrname != 'exception':
            return

        if not is_logger_class(node):
            return

        if not self.linter.is_message_enabled(
            self.MESSAGE_ID, line=node.fromlineno
        ):
            return

        try:
            extra = utils.get_argument_from_call(node, keyword='extra')
        except utils.NoSuchArgumentError:
            return

        if not isinstance(extra, astroid.Dict):
            return

        for key, value in extra.items:
            if key.value == 'stack' and value.value is True:
                self.add_message(self.MESSAGE_ID, node=node)

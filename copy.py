"""
Console

Interactive console widget. Use to add an interactive python interpreter
in a GUI application.

Original by deanhystad available here: https://python-forum.io/thread-25117.html
"""
import code
import collections
import contextlib
import re
import sys
import typing

from PyQt5 import (
    QtCore,
    QtGui,
    QtWidgets,
)

_default_max_history = 100
_default_max_line_continuations = 500


class QCmdLineEdit(QtWidgets.QLineEdit):
    """
    QLineEdit with a history buffer for recalling previous lines.
    The `returnPressed` signal is not used.
    Switching widget focus via the tab key is disabled so that `\t` characters
    can be entered as part of the text.
    """
    line_entered = QtCore.pyqtSignal(str)

    def __init__(self,
                 *,
                 max_history: int = _default_max_history
                 ):
        super().__init__()
        self.history = collections.deque(maxlen=max_history)
        self.history_index = 0
        self.history.appendleft('')

    def event(self, a0: QtCore.QEvent) -> bool:
        if a0.type() == QtCore.QEvent.Type.KeyPress and a0.key() == QtCore.Qt.Key_Tab:
            self.insert('\t')
            return True
        else:
            return super().event(a0)

    def keyPressEvent(self, a0: QtGui.QKeyEvent) -> None:
        if a0.key() == int(QtCore.Qt.Key_Up):
            self._prev()
        elif a0.key() == int(QtCore.Qt.Key_Down):
            self._next()
        elif a0.key() == int(QtCore.Qt.Key_Return):
            self._enter_line()
        else:
            super().keyPressEvent(a0)

    def _enter_line(self) -> None:
        text = self.text()
        self.history_index = 0
        self.history[0] = text
        self.line_entered.emit(text)
        self.history.appendleft('')
        self._update()

    def _prev(self) -> None:
        if self.history_index < len(self.history) - 1:
            self.history_index += 1
            self._update()

    def _next(self) -> None:
        if self.history_index > 0:
            self.history_index -= 1
            self._update()

    def _update(self) -> None:
        self.setText(self.history[self.history_index])


class QCmdConsole(QtWidgets.QWidget):

    def __init__(
        self,
        interpreter: typing.Callable[[str], bool],
        *,
        prompt_text: str = '> ',
        line_continuing_prompt_text: str = '… ',
        max_history: int = _default_max_history,
        max_line_continuations: int = _default_max_line_continuations,
        stdout_foreground: QtGui.QBrush = QtGui.QBrush(QtGui.QColorConstants.Blue),
        stderr_foreground: QtGui.QBrush = QtGui.QBrush(QtGui.QColorConstants.Red),
        parent=None
    ):
        super().__init__(parent=parent)
        self.interpreter = interpreter
        self.buffer = []
        self.prompt_text = prompt_text
        self.line_continuing_prompt_text = line_continuing_prompt_text
        self._prompt_re = re.compile(f'^{re.escape(self.prompt_text)}|{re.escape(self.line_continuing_prompt_text)}')

        # Display for output and stderr
        self.display = QtWidgets.QPlainTextEdit(self)
        # FIXME I think we can just remove this variable
        self.display.setMaximumBlockCount(max_line_continuations)
        self.display.setReadOnly(True)

        # Use color to differentiate input, output and stderr
        self.input_format = self.display.currentCharFormat()

        self.output_format = QtGui.QTextCharFormat(self.input_format)
        self.output_format.setForeground(stdout_foreground)

        self.error_format = QtGui.QTextCharFormat(self.input_format)
        self.error_format.setForeground(stderr_foreground)

        # Display input prompt left of input edit.
        # A QLabel would be more appropriate, but inconveniently, the default
        # background colors are inconsistent
        # FIXME need to go back to QLAbel and adjust palette accordingly
        #  because lineedit is far too wide without setting a fixed size
        self.prompt = QtWidgets.QLineEdit(self)
        self.prompt.setText(self.prompt_text)
        self.prompt.setReadOnly(True)
        self.prompt.setFrame(False)
        self.prompt.setFixedWidth(20)

        # Enter commands here
        self.line_edit = QCmdLineEdit(max_history=max_history)
        self.line_edit.line_entered.connect(self._push)
        self.line_edit.setFrame(False)

        # FIXME remove empty space between input and history
        #  currently one is stuck on the bottom and the other on the top;
        #  textedit probably has a more aggressive size policy than lineedit
        layout = QtWidgets.QGridLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        layout.addWidget(self.display, 0, 0, 1, 2)
        layout.addWidget(self.prompt, 1, 0)
        layout.addWidget(self.line_edit, 1, 1)
        self.setLayout(layout)

        class _StdIn:
            def write(self_, s: str) -> None:
                self._write(s, self.input_format)

        class _StdOut:
            def write(self_, s: str) -> None:
                self._write(s, self.output_format)

        class _StdErr:
            def write(self_, s: str) -> None:
                self._write(s, self.error_format)

        self.stdin = _StdIn()
        self.stdout = _StdOut()
        self.stderr = _StdErr()

    def _push(self, line: str) -> None:
        """
        Execute entered command. Command may span multiple lines
        """
        self.stdin.write(self.prompt.text() + line)
        self.buffer.append(line)

        cmd = '\n'.join(self.buffer)
        more = self.interpreter(cmd)
        if more:
            self.prompt.setText(self.line_continuing_prompt_text)
        else:
            self.prompt.setText(self.prompt_text)
            self.buffer.clear()

    def _write(self, line: str, fmt: QtGui.QTextCharFormat = None) -> None:
        if fmt is not None:
            self.display.setCurrentCharFormat(fmt)
        self.display.appendPlainText(line.rstrip())


if __name__ == '__main__':
    app = QtWidgets.QApplication(sys.argv)
    console = QCmdConsole(interpreter=code.InteractiveConsole().runsource)
    console.setWindowTitle('Console')
    console.setFont(QtGui.QFont('Lucida Sans Typewriter', 10))

    with contextlib.redirect_stdout(console.stdout), contextlib.redirect_stderr(console.stderr):
        console.show()
        sys.exit(app.exec_())

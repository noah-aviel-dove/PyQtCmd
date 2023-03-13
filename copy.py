"""
Console

Interactive console widget. Use to add an interactive python interpreter
in a GUI application.

Original by deanhystad available here: https://python-forum.io/thread-25117.html
"""
import abc
import code
import collections
import contextlib
import io
import sys
import typing

from PyQt5 import (
    QtCore,
    QtGui,
    QtWidgets,
)

_default_max_history = 100
_default_max_lines = 1000


class QCmdLineEdit(QtWidgets.QLineEdit):
    """
    QLineEdit with a history buffer for recalling previous lines using the up
    and down keys.

    The `returnPressed` signal is not used; instead, `line_entered` is emitted
    when the return key is pressed. This is because pressing return empties the
    text buffer and `returnPressed` does not send the text buffer to slots,
    meaning that the text buffer would be lost.

    Switching widget focus via the tab key is disabled so that tabs can be
    entered as part of the text.
    """
    line_entered = QtCore.pyqtSignal(str)

    def __init__(self,
                 *,
                 max_history: int | None = _default_max_history,
                 expand_tab: int | None = None,
                 ):
        """
        :param max_history: The maximum number of history entries that can be
        recalled by pressing the up key. Pass `None` for no limit.
        :param expand_tab: If `None`, tab characters are entered as `\t`.
        Otherwise, they are expanded to the specified number of spaces.
        """
        super().__init__()
        self.expand_tab = expand_tab
        self.history = collections.deque(maxlen=max_history)
        self.history_index = 0
        self.history.appendleft('')

    def event(self, a0: QtCore.QEvent) -> bool:
        return self._intercept_tab(a0) or super().event(a0)

    def keyPressEvent(self, a0: QtGui.QKeyEvent) -> None:
        if a0.key() == QtCore.Qt.Key_Return:
            self._enter_line()
        elif a0.key() == QtCore.Qt.Key_Up:
            self._prev()
        elif a0.key() == QtCore.Qt.Key_Down:
            self._next()
        else:
            super().keyPressEvent(a0)

    def _intercept_tab(self, event: QtCore.QEvent) -> bool:
        is_tab_press = (
            isinstance(event, QtGui.QKeyEvent)
            and event.type() == event.KeyPress
            and event.key() == QtCore.Qt.Key_Tab
        )
        if is_tab_press:
            tab = '\t' if self.expand_tab is None else ' ' * self.expand_tab
            self.insert(tab)
        return is_tab_press

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
    class Stream(abc.ABC, io.TextIOBase):

        def __init__(self,
                     parent: 'QCmdConsole',
                     char_format: QtGui.QTextCharFormat,
                     ):
            self.parent = parent
            self.format = char_format

        def write(self, __s: str) -> int:
            self.parent._display_text(__s, self.format)
            return len(__s)

    class OutputStream(Stream):
        pass

    class InputStream(Stream):

        def __init__(self, parent, char_format):
            super().__init__(parent=parent, char_format=char_format)
            self.buffer = io.StringIO()

        def write(self, __s: str) -> int:
            super().write(__s)
            self.buffer.write(__s)
            if __s.endswith('\n'):
                if not self.parent._exec(self.buffer.getvalue()):
                    self.buffer = io.StringIO()
            return len(__s)

    def __init__(self,
                 interpreter: typing.Callable[[str], bool],
                 *,
                 init_text: str | None = None,
                 prompt_text: str = '> ',
                 line_continuing_prompt_text: str = '… ',
                 max_history: int = _default_max_history,
                 max_lines: int = _default_max_lines,
                 stdout_foreground: QtGui.QBrush | None = None,
                 stderr_foreground: QtGui.QBrush | None = None,
                 parent=None
                 ):
        super().__init__(parent=parent)
        self.interpreter = interpreter
        self.prompt_text = prompt_text
        self.line_continuing_prompt_text = line_continuing_prompt_text

        # Display previously entered lines and output from the interpreter
        self.display = QtWidgets.QPlainTextEdit(self)
        self.display.setReadOnly(True)
        self.display.setMaximumBlockCount(max_lines)

        # Accept new input
        self.editor = QCmdLineEdit(max_history=max_history)
        self.editor.line_entered.connect(self._push)
        self.editor.setFrame(False)

        # FIXME prompt is not horizontally aligned with the display
        self.prompt = QtWidgets.QLabel(self)
        self.prompt.setText(self.prompt_text)
        self.prompt.setBuddy(self.editor)

        # FIXME remove empty space between input and history
        #  currently one is stuck on the bottom and the other on the top;
        #  textedit probably has a more aggressive size policy than lineedit
        layout = QtWidgets.QGridLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        layout.addWidget(self.display, 0, 0, 1, 2)
        layout.addWidget(self.prompt, 1, 0)
        layout.addWidget(self.editor, 1, 1)
        self.setLayout(layout)

        # Use color to differentiate input, output and stderr
        stdin_format = self.display.currentCharFormat()
        stdout_format = QtGui.QTextCharFormat(stdin_format)
        stderr_format = QtGui.QTextCharFormat(stdin_format)
        if stdout_foreground is not None:
            stdout_format.setForeground(stdout_foreground)
        if stderr_foreground is not None:
            stderr_format.setForeground(stderr_foreground)

        self.stdin = self.InputStream(self, stdin_format)
        self.stdout = self.OutputStream(self, stdout_format)
        self.stderr = self.OutputStream(self, stderr_format)

        if init_text is not None:
            self.stdout.write(init_text)

    def _push(self, line: str) -> None:
        self._display_text(self.prompt.text(), self.stdin.format)
        self.stdin.write(line + '\n')

    def _exec(self, input_: str) -> bool:
        more = self.interpreter(input_)
        prompt = self.line_continuing_prompt_text if more else self.prompt_text
        self.prompt.setText(prompt)
        return more

    def _display_text(self,
                      text: str,
                      char_format: QtGui.QTextCharFormat | None = None
                      ) -> None:
        if char_format is not None:
            self.display.setCurrentCharFormat(char_format)
        self.display.insertPlainText(text)


if __name__ == '__main__':
    app = QtWidgets.QApplication(sys.argv)
    console = QCmdConsole(
        init_text=f'Python {sys.version}\n',
        interpreter=code.InteractiveConsole().runsource,
        stdout_foreground=QtGui.QBrush(QtGui.QColorConstants.Cyan),
        stderr_foreground=QtGui.QBrush(QtGui.QColorConstants.Red),
    )
    console.setWindowTitle('Console')
    console.setFont(QtGui.QFont('Lucida Sans Typewriter', 10))
    console.setPalette(QtGui.QPalette(
        QtGui.QColorConstants.Black,
    ))

    with contextlib.redirect_stdout(console.stdout), contextlib.redirect_stderr(console.stderr):
        console.show()
        sys.exit(app.exec_())

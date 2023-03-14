# Emulate the python REPL as a Qt widget
# Adapted from code by deanhystad.
# Original available here: https://python-forum.io/thread-25117.html


import code
import contextlib
import sys

from PyQt5 import (
    QtGui,
    QtWidgets,
)

import PyQtCmd


def main():
    app = QtWidgets.QApplication(sys.argv)
    console = PyQtCmd.QCmdConsole(
        init_text=f'Python {sys.version} on {sys.platform}\n',
        interpreter=code.InteractiveInterpreter().runsource,
        prompt_text='>>> ',
        line_continuing_prompt_text='... ',
        stdout_foreground=QtGui.QBrush(QtGui.QColorConstants.Cyan),
        stderr_foreground=QtGui.QBrush(QtGui.QColorConstants.Red),
    )
    console.setWindowTitle('Python console')
    console.setFont(QtGui.QFont('Lucida Sans Typewriter', 10))
    console.setPalette(QtGui.QPalette(
        QtGui.QColorConstants.Black,
    ))

    with contextlib.redirect_stdout(console.stdout), contextlib.redirect_stderr(console.stderr):
        console.show()
        sys.exit(app.exec_())


if __name__ == '__main__':
    main()

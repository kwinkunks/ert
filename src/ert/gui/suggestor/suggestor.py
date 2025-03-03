import functools
import logging
import webbrowser
from typing import Optional

from PyQt5.QtGui import QCursor
from qtpy.QtCore import Qt
from qtpy.QtWidgets import (
    QFrame,
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QScrollArea,
    QVBoxLayout,
    QWidget,
)

from ert.gui.about_dialog import AboutDialog
from ert.shared.plugins.plugin_manager import ErtPluginManager

from ._colors import BLUE_TEXT
from ._suggestor_message import SuggestorMessage

logger = logging.getLogger(__name__)


def _clicked_help_button(menu_label: str, link: str):
    logger = logging.getLogger(__name__)
    logger.info(f"Pressed help button {menu_label}")
    webbrowser.open(link)


def _clicked_about_button(about_dialog):
    logger = logging.getLogger(__name__)
    logger.info("Pressed help button About")
    about_dialog.show()


LIGHT_GREY = "#f7f7f7"
MEDIUM_GREY = "#eaeaea"
HEAVY_GREY = "#dcdcdc"
DARK_GREY = "#bebebe"
LIGHT_GREEN = "#deedee"
MEDIUM_GREEN = "#007079"
DARK_GREEN = "#004f55"

BUTTON_STYLE = f"""
QPushButton {{
    background-color: {MEDIUM_GREEN};
    color: white;
    border-radius: 4px;
    border: 2px solid {MEDIUM_GREEN};
    height: 36px;
    padding: 0px 16px 0px 16px;
}}
QPushButton:hover {{
    background: {DARK_GREEN};
    border: 2px solid {DARK_GREEN};
}};
"""

LINK_STYLE = f"""
QPushButton {{
    color: {BLUE_TEXT};
    border: 0px solid white;
    margin-left: 34px;
    height: 36px;
    padding: 0px 12px 0px 12px;
    text-decoration: underline;
    text-align: left;
    font-size: 16px;
    padding: 0px;
}}
"""

DISABLED_BUTTON_STYLE = f"""
    background-color: {MEDIUM_GREY};
    color: {DARK_GREY};
    border-radius: 4px;
    border: 2px solid {MEDIUM_GREY};
    height: 36px;
    padding: 0px 16px 0px 16px;
"""

SECONDARY_BUTTON_STYLE = f"""
QPushButton {{
    background-color: {LIGHT_GREY};
    color: {MEDIUM_GREEN};
    border-radius: 4px;
    border: 2px solid {MEDIUM_GREEN};
    height: 36px;
    padding: 0px 16px 0px 16px;
}}
QPushButton:hover {{
    background-color: {LIGHT_GREEN};
}};
"""


class Suggestor(QWidget):
    def __init__(
        self,
        errors,
        warnings,
        deprecations,
        ert_window=None,
        plugin_manager: Optional[ErtPluginManager] = None,
    ):
        super().__init__()
        self.ert_window = ert_window
        self.__layout = QVBoxLayout()
        self.setLayout(self.__layout)
        self.__layout.addWidget(
            QLabel(
                """\
                <p style="font-size: 28px;">Some problems detected</p>
                <p> The following problems were detected while reading
                the ert configuration file. </p>
        """
            )
        )
        self.setWindowTitle("ERT")
        data_widget = QWidget(parent=self)
        self.__layout.addWidget(data_widget)
        self.setStyleSheet(f"background-color: {LIGHT_GREY};")
        self.__layout.setContentsMargins(32, 47, 32, 16)
        self.__layout.setSpacing(32)

        if ert_window is not None:
            data_widget.notifier = ert_window.notifier
        data_layout = QHBoxLayout()
        data_widget.setLayout(data_layout)
        data_layout.setSpacing(16)
        data_layout.setContentsMargins(0, 0, 0, 0)

        data_layout.addWidget(self._problem_area(errors, warnings, deprecations))
        data_layout.addWidget(self._help_panel(plugin_manager))

    def _help_panel(self, plugin_manager):
        help_button_frame = QFrame(parent=self)
        help_button_frame.setContentsMargins(0, 0, 0, 0)
        help_button_frame.setStyleSheet(
            f"""
            background-color: {MEDIUM_GREY};
            border-radius: 4px;
            border: 2px solid {HEAVY_GREY};
            """
        )
        help_button_frame.setMinimumWidth(388)
        help_button_frame.setMaximumWidth(388)
        help_buttons_layout = QVBoxLayout()
        help_buttons_layout.setContentsMargins(0, 30, 20, 20)
        help_button_frame.setLayout(help_buttons_layout)

        help_links = plugin_manager.get_help_links() if plugin_manager else {}

        help_header = QLabel("Helpful links", parent=self)
        help_header.setContentsMargins(0, 0, 0, 0)
        help_header.setStyleSheet(
            f"font-size: 24px; color: {BLUE_TEXT}; border: none; margin-left: 30px;"
        )
        help_buttons_layout.addWidget(help_header, alignment=Qt.AlignmentFlag.AlignTop)

        separator = QFrame(parent=self)
        separator.setFrameShape(QFrame.HLine)
        separator.setStyleSheet(f"color: {HEAVY_GREY};")
        separator.setFixedWidth(388)
        help_buttons_layout.addWidget(separator)

        for menu_label, link in help_links.items():
            button = QPushButton(menu_label, parent=self)
            button.setStyleSheet(LINK_STYLE)
            button.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
            button.setObjectName(menu_label)
            button.clicked.connect(
                functools.partial(_clicked_help_button, menu_label, link)
            )
            help_buttons_layout.addWidget(button)

        about_button = QPushButton("About", parent=self)
        about_button.setStyleSheet(LINK_STYLE)
        about_button.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        about_button.setObjectName("about_button")
        help_buttons_layout.addWidget(about_button)
        help_buttons_layout.addStretch(-1)

        diag = AboutDialog(self)
        about_button.clicked.connect(lambda: _clicked_about_button(diag))
        return help_button_frame

    def _problem_area(self, errors, warnings, deprecations):
        problem_area = QWidget(parent=self)
        problem_area.setContentsMargins(0, 0, 0, 0)
        area_layout = QVBoxLayout()
        problem_area.setLayout(area_layout)
        area_layout.setContentsMargins(0, 0, 0, 0)
        area_layout.addWidget(self._messages(errors, warnings, deprecations))
        area_layout.addWidget(self._action_buttons())
        return problem_area

    def _action_buttons(self):
        def run_pressed():
            assert self.ert_window is not None
            self.ert_window.show()
            self.ert_window.activateWindow()
            self.ert_window.raise_()
            self.ert_window.adjustSize()
            self.close()

        run = QPushButton("Open ERT")
        give_up = QPushButton("Cancel")
        if self.ert_window is None:
            run.setStyleSheet(DISABLED_BUTTON_STYLE)
            run.setEnabled(False)
            give_up.setStyleSheet(BUTTON_STYLE)
        else:
            run.setStyleSheet(BUTTON_STYLE)
            run.setEnabled(True)
            give_up.setStyleSheet(SECONDARY_BUTTON_STYLE)

        run.setObjectName("run_ert_button")
        run.pressed.connect(run_pressed)
        give_up.pressed.connect(self.close)
        buttons = QWidget(parent=self)
        buttons_layout = QHBoxLayout()
        buttons_layout.insertStretch(-1, -1)
        buttons_layout.setContentsMargins(0, 24, 0, 0)
        buttons_layout.addWidget(run)
        buttons_layout.addWidget(give_up)
        buttons.setLayout(buttons_layout)
        return buttons

    def _messages(self, errors, warnings, deprecations):
        suggest_msgs = QWidget(parent=self)
        suggest_msgs.setContentsMargins(0, 0, 16, 0)
        suggest_layout = QGridLayout()
        suggest_layout.setContentsMargins(0, 0, 0, 0)
        suggest_layout.setColumnMinimumWidth(0, 450)
        suggest_layout.setSpacing(24)

        column = 0
        row = 0
        num = 0
        for msg in errors:
            suggest_layout.addWidget(SuggestorMessage.error_msg(msg), row, column)
            if column:
                row += 1
            column = (column + 1) % 2
            num += 1
        for msg in warnings:
            suggest_layout.addWidget(SuggestorMessage.warning_msg(msg), row, column)
            if column:
                row += 1
            column = (column + 1) % 2
            num += 1
        for msg in deprecations:
            suggest_layout.addWidget(SuggestorMessage.deprecation_msg(msg), row, column)
            if column:
                row += 1
            column = (column + 1) % 2
            num += 1
        suggest_layout.setRowStretch(row + 1, 1)
        width = 1440
        height = 1024
        if num <= 1:
            width -= 450
        else:
            suggest_layout.setColumnMinimumWidth(1, 450)
            suggest_layout.setColumnStretch(2, 1)
        if row < 4:
            height -= (4 - (row + column)) * 150
        self.resize(width, height)

        suggest_msgs.setLayout(suggest_layout)
        scroll = QScrollArea()
        scroll.setStyleSheet(
            f"""
            QScrollArea {{
                border: none;
                width: 128px;
            }}
            QScrollBar {{
                border: none;
                background-color: {LIGHT_GREY};
                width: 10px;
            }}
            QScrollBar::handle {{
                border: none;
                background-color: {HEAVY_GREY};
                border-radius: 4px;
            }}
            QScrollBar::sub-line:vertical, QScrollBar::add-line:vertical {{
                background: none;
            }}
        """
        )
        scroll.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        scroll.setWidgetResizable(True)
        scroll.setWidget(suggest_msgs)
        scroll.setContentsMargins(0, 0, 0, 0)
        return scroll

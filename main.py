"""
CrazyToolBox, a web3 utilities GUI toolbox.
© 2023 Telefónica Digital España S.L.

This program is free software: you can redistribute it and/or modify
it under the terms of the GNU Affero General Public License as
published by the Free Software Foundation, either version 3 of the
License, or (at your option) any later version.
 
This program is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
GNU Affero General Public License for more details.

You should have received a copy of the GNU Affero General Public License
along with this program.  If not, see <https://www.gnu.org/licenses/>.
"""

import threading
import os

from PySide6.QtCore import QObject, Signal, Slot, QFile, QTimer
from PySide6.QtUiTools import QUiLoader
from PySide6.QtWidgets import (
    QApplication,
    QCheckBox,
    QComboBox,
    QHBoxLayout,
    QPlainTextEdit,
    QPushButton,
    QSizePolicy,
    QStackedWidget,
    QTabWidget,
    QTextEdit,
)
import pyperclip

from src.custom_types import MOST_USED_SOLIDITY_DATA_TYPES, CURRENCY_TYPES, MOST_USED_CURRENCY_TYPES
from src.toolbox_core import ToolBoxCore

MAX_PARAMS = 8


#####################
#       UTILS       #
#####################
def update_items():
    global weiConverterFrom, weiConverterTo, advancedModeCheckbox

    weiConverterFrom.clear()
    weiConverterTo.clear()

    items_to_add = CURRENCY_TYPES if advancedModeCheckbox.isChecked() else MOST_USED_CURRENCY_TYPES
    weiConverterFrom.addItems(items_to_add)
    weiConverterTo.addItems(items_to_add)


def add_list_widget_item(function_selector_encoder):
    global paramsLayout, result_to_copy, result_signal

    if paramsLayout.count() >= MAX_PARAMS - 1:
        result_signal.result_to_copy.emit("")
        result_signal.result.emit("Max params reached! To add more params, use the advanced mode.")

    if paramsLayout.count() >= MAX_PARAMS:
        return

    combo_widget = QComboBox()
    combo_widget.addItem("-")
    combo_widget.addItems(MOST_USED_SOLIDITY_DATA_TYPES)
    combo_widget.setMaximumHeight(30)
    combo_widget.setMinimumHeight(30)
    combo_widget.setSizePolicy(QSizePolicy.Ignored, QSizePolicy.Fixed)

    combo_widget.currentIndexChanged.connect(
        lambda: function_selector_encoder(
            functionSelectorNameInput.toPlainText(), [paramsLayout.itemAt(i).widget().currentText() for i in range(paramsLayout.count())]
        )
    )

    paramsLayout.addWidget(combo_widget)

    enable_disable_buttons()


def remove_list_widget_item():
    global paramsLayout, addParamButton, removeParamButton

    item = paramsLayout.itemAt(paramsLayout.count() - 1)
    if item is not None:
        widget = item.widget()
        paramsLayout.removeWidget(widget)
        widget.deleteLater()

    enable_disable_buttons()


def enable_disable_buttons():
    global paramsLayout, addParamButton, removeParamButton

    if paramsLayout.count() >= MAX_PARAMS:
        addParamButton.setEnabled(False)
        removeParamButton.setEnabled(True)
    elif paramsLayout.count() <= 0:
        addParamButton.setEnabled(True)
        removeParamButton.setEnabled(False)
    else:
        addParamButton.setEnabled(True)
        removeParamButton.setEnabled(True)


def copy_result():
    global result_to_copy, copyButton

    if result_to_copy != "":
        # Convert markdown to plain text
        result_to_copy_plain = result_to_copy.replace("<br />", "\n").replace("**", "").replace("__", "")

        # Copy to clipboard
        pyperclip.copy(result_to_copy_plain)
        copyButton.setText("Copied!")
        QTimer.singleShot(1000, lambda: copyButton.setText("Copy"))


def reset_gui():
    global result_signal

    result_signal.result_to_copy.emit("")
    result_signal.result.emit("")
    result_signal.function_signature.emit("")


#####################
#      SIGNALS      #
#####################
class ResultSignal(QObject):
    result_to_copy = Signal(str)
    result = Signal(str)
    function_signature = Signal(str)


@Slot()
def update_output_label(text):
    global outputLabel

    outputLabel.setMarkdown(text)


@Slot()
def update_result_to_copy(text):
    global result_to_copy, copyButton

    result_to_copy = text
    if result_to_copy != "":
        copyButton.setEnabled(True)
    else:
        copyButton.setEnabled(False)


@Slot()
def update_function_signature(text):
    global functionSignatureOutput

    functionSignatureOutput.setPlainText(text)


if __name__ == "__main__":
    # Load the UI
    app = QApplication([])
    ui_file = QFile(os.path.join(os.path.dirname(__file__), "view", "main.ui"))
    ui_file.open(QFile.ReadOnly)
    loader = QUiLoader()

    # Set the window
    window = loader.load(ui_file)
    window.setWindowTitle("Crazy ToolBox")

    # Connect the signals
    result_signal = ResultSignal()
    result_signal.result_to_copy.connect(update_result_to_copy)
    result_signal.result.connect(update_output_label)
    result_signal.function_signature.connect(update_function_signature)

    # Create the core
    toolBoxCore = ToolBoxCore(result_signal)

    # General
    result_to_copy = ""
    copyButton = window.findChild(QPushButton, "copyButton")
    outputLabel = window.findChild(QTextEdit, "outputLabel")
    tabWidget = window.findChild(QTabWidget, "tabWidget")

    copyButton.clicked.connect(copy_result)
    tabWidget.currentChanged.connect(reset_gui)

    # Wei converter
    weiConverterInput = window.findChild(QPlainTextEdit, "weiConverterInput")
    weiConverterFrom = window.findChild(QComboBox, "weiConverterFrom")
    weiConverterTo = window.findChild(QComboBox, "weiConverterTo")
    advancedModeCheckbox = window.findChild(QCheckBox, "advancedModeCheckbox")

    weiConverterInput.textChanged.connect(
        lambda: toolBoxCore.wei_converter(weiConverterInput.toPlainText(), weiConverterFrom.currentText(), weiConverterTo.currentText())
    )

    weiConverterFrom.currentIndexChanged.connect(
        lambda: toolBoxCore.wei_converter(weiConverterInput.toPlainText(), weiConverterFrom.currentText(), weiConverterTo.currentText())
    )

    weiConverterTo.currentIndexChanged.connect(
        lambda: toolBoxCore.wei_converter(weiConverterInput.toPlainText(), weiConverterFrom.currentText(), weiConverterTo.currentText())
    )

    advancedModeCheckbox.stateChanged.connect(update_items)

    # Function selector encoder view
    advancedModeCheckbox2 = window.findChild(QCheckBox, "advancedModeCheckbox2")
    fsEncoderStackedWidget = window.findChild(QStackedWidget, "fsEncoderStackedWidget")

    fsEncoderStackedWidget.currentChanged.connect(reset_gui)
    advancedModeCheckbox2.stateChanged.connect(
        lambda: fsEncoderStackedWidget.setCurrentIndex(1 if advancedModeCheckbox2.isChecked() else 0)
    )

    # Function selector encoder basic
    addParamButton = window.findChild(QPushButton, "addParamButton")
    removeParamButton = window.findChild(QPushButton, "removeParamButton")
    functionSelectorNameInput = window.findChild(QPlainTextEdit, "functionSelectorNameInput")
    functionSignatureOutput = window.findChild(QPlainTextEdit, "functionSignatureOutput")
    paramsLayout = window.findChild(QHBoxLayout, "paramsLayout")

    addParamButton.clicked.connect(lambda: add_list_widget_item(toolBoxCore.function_selector_encoder))
    removeParamButton.clicked.connect(remove_list_widget_item)

    functionSelectorNameInput.textChanged.connect(
        lambda: toolBoxCore.function_selector_encoder(
            functionSelectorNameInput.toPlainText(), [paramsLayout.itemAt(i).widget().currentText() for i in range(paramsLayout.count())]
        )
    )

    # Function selector encoder advanced
    functionSelectorSignatureInput = window.findChild(QPlainTextEdit, "functionSelectorSignatureInput")

    functionSelectorSignatureInput.textChanged.connect(
        lambda: toolBoxCore.function_selector_encoder_advanced(functionSelectorSignatureInput.toPlainText())
    )

    # Function selector decoder
    functionSelectorDecoderInput = window.findChild(QPlainTextEdit, "functionSelectorDecoderInput")
    functionSelectorDecoderInput.textChanged.connect(
        lambda: QTimer.singleShot(1000, lambda: toolBoxCore.function_selector_decoder(functionSelectorDecoderInput.toPlainText()))
    )

    # Transaction input decoder
    transactionInputDecoderInput = window.findChild(QPlainTextEdit, "transactionInputDecoderInput")
    transactionInputDecoderInput.textChanged.connect(
        lambda: QTimer.singleShot(
            1000,
            lambda: threading.Thread(
                target=toolBoxCore.decode_transaction_input, args=(transactionInputDecoderInput.toPlainText(),)
            ).start(),
        )
    )

    # Keccak256 hash
    keccak256HashInput = window.findChild(QPlainTextEdit, "keccak256HashInput")
    keccak256HashInput.textChanged.connect(lambda: toolBoxCore.keccak256_hash(keccak256HashInput.toPlainText()))

    # EIP55 Validator
    eip55ValidatorInput = window.findChild(QPlainTextEdit, "eip55ValidatorInput")
    eip55ValidatorInput.textChanged.connect(lambda: toolBoxCore.eip55_validator(eip55ValidatorInput.toPlainText()))

    # Get signature owner
    signatureMessageHashInput = window.findChild(QPlainTextEdit, "signatureMessageHashInput")
    signatureInput = window.findChild(QPlainTextEdit, "signatureInput")

    signatureMessageHashInput.textChanged.connect(
        lambda: toolBoxCore.get_signer_owner(signatureMessageHashInput.toPlainText(), signatureInput.toPlainText())
    )

    signatureInput.textChanged.connect(
        lambda: toolBoxCore.get_signer_owner(signatureMessageHashInput.toPlainText(), signatureInput.toPlainText())
    )

    # Show the window
    window.show()
    app.exec()

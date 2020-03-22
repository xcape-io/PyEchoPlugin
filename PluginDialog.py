#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
PluginDialog.py
MIT License (c) Marie Faure <dev at faure dot systems>

Dialog to control PluginProps app running on Raspberry.
"""

import os, re

from PluginSettingsDialog import PluginSettingsDialog
from AppletDialog import AppletDialog
from LedWidget import LedWidget
from PyQt5.QtGui import QIcon, QPalette
from PyQt5.QtCore import Qt, pyqtSignal, pyqtSlot, QSize, QPoint, QSettings
from PyQt5.QtWidgets import QHBoxLayout, QVBoxLayout, QFrame
from PyQt5.QtWidgets import QTextEdit, QPlainTextEdit, QPushButton, QComboBox


class PluginDialog(AppletDialog):
    aboutToClose = pyqtSignal()
    publishMessage = pyqtSignal(str, str)
    switchLed = pyqtSignal(str, str)

    # __________________________________________________________________
    def __init__(self, title, icon, logger):
        super().__init__(title, icon, logger)

        # always on top sometimes doesn't work
        self.setAttribute(Qt.WA_AlwaysStackOnTop)
        self.setWindowFlags(self.windowFlags()
                            & ~Qt.WindowContextHelpButtonHint | Qt.WindowStaysOnTopHint)

        self._props_inbox = False
        self._room_admin = False

    # __________________________________________________________________
    def _buildUi(self):
        self._options = {}
        if os.path.isfile('definitions.ini'):
            definitions = QSettings('definitions.ini', QSettings.IniFormat)
            for group in definitions.childGroups():
                definitions.beginGroup(group)
                if group == "options":
                    for key in definitions.childKeys():
                        self._options[key] = definitions.value(key)
                definitions.endGroup()

        main_layout = QVBoxLayout()
        main_layout.setSpacing(12)

        self._led = LedWidget(self.tr("Arduino Echo"), QSize(40, 20))
        self._led.setRedAsBold(True)
        self._led.setRedAsRed(True)
        self._led.switchOn('gray')

        settings_button = QPushButton()
        settings_button.setIcon(QIcon("./images/settings.svg"))
        settings_button.setFlat(True)
        settings_button.setToolTip(self.tr("Configuration"))
        settings_button.setIconSize(QSize(16, 16))
        settings_button.setFixedSize(QSize(24, 24))

        header_layout = QHBoxLayout()
        header_layout.addWidget(self._led)
        header_layout.addWidget(settings_button, Qt.AlignRight)
        main_layout.addLayout(header_layout)

        self._selectionComboBox = QComboBox()
        self.loadMessages();
        main_layout.addWidget(self._selectionComboBox)

        self._props_messages_input = QPlainTextEdit()
        self._props_messages_input.setFrameShape(QFrame.NoFrame)
        self._props_messages_input.setCursorWidth(8)
        main_layout.addWidget(self._props_messages_input)

        buttons_layout = QHBoxLayout()
        main_layout.addLayout(buttons_layout)

        send_button = QPushButton(self.tr("Send"))
        buttons_layout.addWidget(send_button)

        clear_button = QPushButton(self.tr("Clear"))
        buttons_layout.addWidget(clear_button)

        self._props_messages_display = QTextEdit()
        self._props_messages_display.setReadOnly(True)
        main_layout.addWidget(self._props_messages_display)

        main_layout.addStretch(0)

        self.setLayout(main_layout)

        self._selectionComboBox.activated.connect(self.onSelectionBox)
        clear_button.pressed.connect(self.onClearButton)
        send_button.pressed.connect(self.onSendButton)
        settings_button.pressed.connect(self.settings)
        self.switchLed.connect(self._led.switchOn)

    # __________________________________________________________________
    @pyqtSlot(str, str)
    def onMessage(self, topic, message):
        if topic == self._room_admin and not self._props_inbox:
            self._logger.warning(
                "{0} : {1}".format(self.tr("Room administrator topic is not defined, message ignored"), "---"))
        else:
            if message == 'yes':
                self._props_messages_display.setVisible(True)
            elif message == 'no':
                self._props_messages_display.setVisible(False)
            else:
                self._logger.warning(
                    "{0} : {1}".format(message, self.tr("unexpected message from Room administrator topic")))

    # __________________________________________________________________
    @pyqtSlot(str)
    def onPropsMessage(self, message):
        if message.startswith("DISCONNECTED"):
            self._led.switchOn('yellow')
        else:
            if self._led.color() != 'green':
                self._led.switchOn('green')
            self._props_messages_display.append(message)

    # __________________________________________________________________
    @pyqtSlot()
    def onClearButton(self):
        if not self._props_inbox:
            self._logger.warning(
                "{0} : {1}".format(self.tr("Echo props inbox is not defined, message ignored"), "---"))
        else:
            self.publishMessage.emit(self._props_inbox, "echo:---")
        self._props_messages_input.clear()
        self._selectionComboBox.setCurrentIndex(0)

    # __________________________________________________________________
    @pyqtSlot()
    def onSendButton(self):
        message = self._props_messages_input.toPlainText().strip()
        if not self._props_inbox:
            self._logger.warning(
                "{0} : {1}".format(self.tr("Echo props inbox is not defined, message ignored"), message))
        else:
            if len(message) == 0:
                message = "---"
            self.publishMessage.emit(self._props_inbox, "echo:" + message)
            self._props_messages_input.clear()
        self._selectionComboBox.setCurrentIndex(0)

    # __________________________________________________________________
    @pyqtSlot('int')
    def onSelectionBox(self, index):
        self._props_messages_input.setPlainText(self._selectionComboBox.itemData(index))

    # __________________________________________________________________
    def setPropsInboxTopic(self, inbox):
        self._props_inbox = inbox

    # __________________________________________________________________
    def setRoomAdminTopic(self, topic):
        self._room_admin = topic

    # __________________________________________________________________
    def loadMessages(self):
        settings = QSettings("settings.ini", QSettings.IniFormat);
        settings.setIniCodec("UTF-8");
        settings.beginGroup("Parameters")
        lang = settings.value('param', 'en')
        settings.endGroup()

        predefined_messages = {}
        if lang == 'fr':
            predefined_messages["Charger un message..."] = None
            predefined_messages['Bonjour le Monde'] = 'Bonjour le Monde'
            predefined_messages['Salut les copains'] = 'Salut les copains!\nComment allez-vous?'
        else:
            predefined_messages["Load message..."] = None
            predefined_messages['Hello World'] = 'Hello World'
            predefined_messages['Hello folks'] = 'Hello folks!\nHow are you doing?'
        self._selectionComboBox.clear()
        for key in predefined_messages:
            self._selectionComboBox.addItem(key, predefined_messages[key])

    # __________________________________________________________________
    def closeEvent(self, e):
        self.aboutToClose.emit()

    # __________________________________________________________________
    @pyqtSlot()
    def settings(self):
        dlg = PluginSettingsDialog(self._logger)
        dlg.setModal(True)
        dlg.move(self.pos() + QPoint(20, 20))
        dlg.exec()
        self.loadMessages()

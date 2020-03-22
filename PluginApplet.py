#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
PluginApplet.py
MIT License (c) Marie Faure <dev at faure dot systems>

PluginApplet application extends MqttApplet.
"""

from constants import *
import argparse, os
import logging, logging.config
from MqttApplet import MqttApplet
from PluginDialog import PluginDialog
from PyQt5.QtCore import pyqtSignal, pyqtSlot
from PyQt5.QtCore import QTranslator, QDir, QSettings


class PluginApplet(MqttApplet):
    propsMessageReceived = pyqtSignal(str)

    # __________________________________________________________________
    def __init__(self, argv, client, debugging_mqtt=False):
        super().__init__(argv, client, debugging_mqtt)

        settings = QSettings("settings.ini", QSettings.IniFormat);
        settings.setIniCodec("UTF-8");
        settings.beginGroup("MQTT")

        parser = argparse.ArgumentParser()
        parser.add_argument("-s", "--server", help="change MQTT server host", nargs=1)
        parser.add_argument("-p", "--port", help="change MQTT server port", nargs=1, type=int)
        parser.add_argument("-d", "--debug", help="set DEBUG log level", action='store_true')
        parser.add_argument("-l", "--logger", help="use logging config file", nargs=1)
        parser.add_argument("-f", "--french", help="run in French", action='store_true')
        args = vars(parser.parse_args())

        if args['server']:
            self._mqttServerHost = args['server'][0]
            settings.setValue('host', self._mqttServerHost)

        if args['port']:
            self._mqttServerPort = args['port'][0]
            settings.setValue('port', self._mqttServerPort)

        if args['logger'] and os.path.isfile(args['logger']):
            logging.config.fileConfig(args['logger'])
            if args['debug']:
                self._logger = logging.getLogger('debug')
                self._logger.setLevel(logging.DEBUG)
            else:
                self._logger = logging.getLogger('production')
                self._logger.setLevel(logging.INFO)
        elif os.path.isfile('logging.ini'):
            logging.config.fileConfig('logging.ini')
            if args['debug']:
                self._logger = logging.getLogger('debug')
                self._logger.setLevel(logging.DEBUG)
            else:
                self._logger = logging.getLogger('production')
                self._logger.setLevel(logging.INFO)
        else:
            if args['debug']:
                self._logger = logging.getLogger('debug')
                self._logger.setLevel(logging.DEBUG)
            else:
                self._logger = logging.getLogger('production')
                self._logger.setLevel(logging.INFO)
            ch = logging.FileHandler('plugin.log', 'w')
            ch.setLevel(logging.INFO)
            self._logger.addHandler(ch)

        self.translator = QTranslator()
        if args['french']:
            try:
                if self.translator.load(TRANSLATOR_FR, QDir.currentPath()):
                    self.installTranslator(self.translator)
            except:
                pass

        self.setApplicationDisplayName(APPDISPLAYNAME)

        # on_message per topic callbacks
        try:
            mqtt_sub_props = self._definitions['mqtt-sub-props']
            self._mqttClient.message_callback_add(mqtt_sub_props, self.mqttOnMessageFromProps)
        except Exception as e:
            self._logger.error(self.tr("Plugin sub topic definition is missing"))
            self._logger.debug(e)

        # on_message default callback
        self._mqttClient.on_message = self.mqttOnMessage

        self._PluginDialog = PluginDialog(self.tr("Echo"), './room.png', self._logger)
        self._PluginDialog.setPropsInboxTopic(self._definitions['mqtt-pub-props'])
        self._PluginDialog.setRoomAdminTopic(self._definitions['mqtt-sub-control-administrator'])
        self._PluginDialog.aboutToClose.connect(self.exitOnClose)
        self._PluginDialog.publishMessage.connect(self.publishMessage)
        self.propsMessageReceived.connect(self._PluginDialog.onPropsMessage)
        self.messageReceived.connect(self._PluginDialog.onMessage)
        self._PluginDialog.show()

    # __________________________________________________________________
    @pyqtSlot()
    def exitOnClose(self):
        self._logger.info(self.tr("exitOnClose "))
        self.quit()

    # __________________________________________________________________
    def mqttOnMessageFromProps(self, client, userdata, msg):
        message = None
        try:
            message = msg.payload.decode(encoding="utf-8", errors="strict")
        except:
            pass

        if message:
            self._logger.info(
                self.tr("Message received from Plugin props : '") + message + self.tr("' in ") + msg.topic)
            self.propsMessageReceived.emit(message)
        else:
            self._logger.warning(
                "{0} {1}".format(self.tr("Decoding MQTT message from Plugin props failed on"), msg.topic))

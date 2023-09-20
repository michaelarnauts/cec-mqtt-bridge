#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import configparser as ConfigParser
import logging
import os
import paho.mqtt.client as mqtt
import threading
import time

from lib import hdmicec, lirc

LOGGER = logging.getLogger('bridge')
logging.basicConfig(level=logging.INFO, format='%(asctime)s [%(name)s] %(funcName)s: %(message)s')

# Default configuration
DEFAULT_CONFIGURATION = {
    'mqtt': {
        'broker': 'localhost',
        'name': 'CEC Bridge',
        'port': 1883,
        'prefix': 'media',
        'user': '',
        'password': '',
        'tls': 0,
    },
    'cec': hdmicec.DEFAULT_CONFIGURATION,
    'ir': lirc.DEFAULT_CONFIGURATION,
}


class Bridge:

    def __init__(self):
        self.config = self._load_config()

        def mqtt_on_message(client: mqtt, userdata, message):
            """Run mqtt callback in a seperate thread."""
            thread = threading.Thread(target=self.mqtt_on_message, args=(client, userdata, message))
            thread.start()

        # Setup MQTT
        LOGGER.info("Initialising MQTT...")
        self.mqtt_client = mqtt.Client(self.config['mqtt']['name'])
        self.mqtt_client.on_connect = self.mqtt_on_connect
        self.mqtt_client.on_message = mqtt_on_message
        if self.config['mqtt']['user']:
            self.mqtt_client.username_pw_set(self.config['mqtt']['user'], password=self.config['mqtt']['password']);
        if int(self.config['mqtt']['tls']) == 1:
            self.mqtt_client.tls_set()
        self.mqtt_client.will_set(self.config['mqtt']['prefix'] + '/bridge/status', 'offline', qos=1, retain=True)
        # Connect with MQTT Broker as a loop so it gets retried every 10 seconds.
        connect_flag=False
        while True:
            try:
                self.mqtt_client.connect(self.config['mqtt']['broker'], int(self.config['mqtt']['port']), 60)
                connect_flag=True
                break
            except:
                if connect_flag == False:
                    LOGGER.info("Waiting for MQTT connection")
                time.sleep(10)             # sleep for 10 seconds and then retry forever
            continue

        self.mqtt_client.loop_start()

        # Setup HDMI-CEC
        if int(self.config['cec']['enabled']) == 1:
            self.cec_class = hdmicec.HdmiCec(port=self.config['cec']['port'],
                                             name=self.config['cec']['name'],
                                             devices=[int(x) for x in self.config['cec']['devices'].split(',')],
                                             mqtt_send=self.mqtt_publish)

        # Setup IR
        if int(self.config['ir']['enabled']) == 1:
            self.ir_class = lirc.Lirc(mqtt_send=self.mqtt_publish)

    @staticmethod
    def _load_config(filename='config.ini'):
        config = DEFAULT_CONFIGURATION

        try:
            # Load all sections and overwrite default configuration
            config_parser = ConfigParser.ConfigParser()
            if config_parser.read(filename):
                for section in config_parser.sections():
                    config[section].update(dict(config_parser.items(section)))

            # Override with environment variables
            for section in config:
                for key, value in config[section].items():
                    env = os.getenv(section.upper() + '_' + key.upper());
                    if env:
                        config[section][key] = type(value)(env)

        except Exception as e:
            raise Exception("Could not configure: %s" % str(e))

        # Do some checks
        if (not int(config['cec']['enabled']) == 1) and \
                (not int(config['ir']['enabled']) == 1):
            raise Exception('IR and CEC are both disabled. Can\'t continue.')

        return config

    def mqtt_on_connect(self, client: mqtt, userdata, flags, rc):
        # Subscribe to CEC commands
        if int(self.config['cec']['enabled']) == 1:
            client.subscribe([
                (self.config['mqtt']['prefix'] + '/cec/power/+/set', 0),
                (self.config['mqtt']['prefix'] + '/cec/volume/set', 0),
                (self.config['mqtt']['prefix'] + '/cec/mute/set', 0),
                (self.config['mqtt']['prefix'] + '/cec/tx', 0),
            ])

        # Subscribe to IR commands
        if int(self.config['ir']['enabled']) == 1:
            client.subscribe([
                (self.config['mqtt']['prefix'] + '/ir/+/tx', 0)
            ])

        # Publish birth message
        self.mqtt_publish('bridge/status', 'online', qos=1, retain=True)

    def mqtt_publish(self, topic, message=None, qos=0, retain=False):
        """Publish a MQTT message"""
        LOGGER.debug('Send to topic %s: %s', topic, message)
        self.mqtt_client.publish(self.config['mqtt']['prefix'] + '/' + topic, message, qos=qos, retain=retain)

    def mqtt_on_message(self, client: mqtt, userdata, message):

        # Decode topic and split off the prefix
        topic = message.topic.replace(self.config['mqtt']['prefix'], '').split('/')[1:]
        action = message.payload.decode()
        LOGGER.info("Command received: %s (%s)" % (topic, message.payload))

        if hasattr(self, 'cec_class') and topic[0] == 'cec':

            if topic[1] == 'power':
                device = int(topic[2])
                if action == 'on':
                    self.cec_class.power_on(device)
                    return
                if action == 'off':
                    self.cec_class.power_off(device)
                    return
                raise Exception("Unknown power command: %s (%s)" % (topic, action))

            if topic[1] == 'volume':
                if action == 'up':
                    self.cec_class.volume_up()
                    return
                if action == 'down':
                    self.cec_class.volume_down()
                    return
                if action.isdigit() and int(action) <= 100:
                    self.cec_class.volume_set(int(action))
                    return
                raise Exception("Unknown volume command: %s (%s)" % (topic, action))

            if topic[1] == 'mute':
                if action == 'on':
                    self.cec_class.volume_mute()
                    return
                if action == 'off':
                    self.cec_class.volume_unmute()
                    return
                raise Exception("Unknown mute command: %s (%s)" % (topic, action))

            if topic[1] == 'tx':
                commands = message.payload.decode().split(',')
                for command in commands:
                    self.cec_class.tx_command(command)
                return

    def cleanup(self):
        """Terminates the connection."""
        self.mqtt_client.loop_stop()
        self.mqtt_publish('bridge/status', 'offline', qos=1, retain=True)
        self.mqtt_client.disconnect()


if __name__ == '__main__':
    bridge = Bridge()

    try:
        while True:
            # Refresh CEC state
            if bridge.cec_class:
                bridge.cec_class.refresh()

            # Refresh every 5 seconds
            time.sleep(10)

    except KeyboardInterrupt:
        bridge.cleanup()

    except RuntimeError:
        bridge.cleanup()

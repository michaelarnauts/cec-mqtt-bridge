#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import paho.mqtt.client as mqtt
import subprocess
import time
import re
import configparser as ConfigParser
import threading
import os

# Default configuration
config = {
    'mqtt': {
        'broker': 'localhost',
        'port': 1883,
        'prefix': 'media',
        'user': os.environ.get('MQTT_USER'),
        'password': os.environ.get('MQTT_PASSWORD'),
    },
    'cec': {
        'enabled': 0,
        'id': 1,
        'port': 'RPI',
        'devices': '0,1,2,3,4,5,6,7,8,9,10,11,12,13,14,15',
    },
    'ir': {
        'enabled': 0,
    }
}


def mqtt_on_connect(client, userdata, rc):
    """@type client: paho.mqtt.client """

    print("Connection returned result: " + str(rc))

    # Subscribe to CEC commands
    if int(config['cec']['enabled']) == 1:
        client.subscribe([
            (config['mqtt']['prefix'] + '/cec/cmd', 0),
            (config['mqtt']['prefix'] + '/cec/+/cmd', 0),
            (config['mqtt']['prefix'] + '/cec/tx', 0)
        ])

    # Subscribe to IR commands
    if int(config['ir']['enabled']) == 1:
        client.subscribe([
            (config['mqtt']['prefix'] + '/ir/+/tx', 0)
        ])


def mqtt_on_message(client, userdata, message):
    """@type client: paho.mqtt.client """

    try:

        # Decode topic
        cmd = message.topic.replace(config['mqtt']['prefix'], '').strip('/')
        print("Command received: %s (%s)" % (cmd, message.payload))

        split = cmd.split('/')

        if split[0] == 'cec':

            if split[1] == 'cmd':

                action = message.payload.decode()

                if action == 'mute':
                    cec_client.AudioMute()
                    return

                if action == 'unmute':
                    cec_client.AudioUnmute()
                    return

                if action == 'voldown':
                    cec_client.VolumeDown()
                    return

                if action == 'volup':
                    cec_client.VolumeUp()
                    return

                raise Exception("Unknown command (%s)" % action)

            if split[1] == 'tx':
                commands = message.payload.decode().split(',')
                for command in commands:
                    print(" Sending raw: %s" % command)
                    cec_send(command)
                return

            if split[2] == 'cmd':

                action = message.payload.decode()

                if action == 'on':
                    id = int(split[1])
                    cec_send('44:6D', id=id)
                    mqtt_send(config['mqtt']['prefix'] + '/cec/' + str(id), 'on', True)
                    return

                if action == 'off':
                    id = int(split[1])
                    cec_send('36', id=id)
                    mqtt_send(config['mqtt']['prefix'] + '/cec/' + str(id), 'off', True)
                    return

                raise Exception("Unknown command (%s)" % action)

        if split[0] == 'ir':

            if split[2] == 'tx':
                remote = split[1]
                key = message.payload.decode()
                ir_send(remote, key)
                return

    except Exception as e:
        print("Error during processing of message: ", message.topic, message.payload, str(e))


def mqtt_send(topic, value, retain=False):
    mqtt_client.publish(topic, value, retain=retain)


def cec_on_message(level, time, message):
    if level == cec.CEC_LOG_TRAFFIC:

        # Send raw command to mqtt
        m = re.search('>> ([0-9a-f:]+)', message)
        if m:
            mqtt_send(config['mqtt']['prefix'] + '/cec/rx', m.group(1))

        # Report Power Status
        m = re.search('>> ([0-9a-f])[0-9a-f]:90:([0-9a-f]{2})', message)
        if m:
            id = int(m.group(1), 16)
            # power = cec_client.PowerStatusToString(int(m.group(2)))
            if (m.group(2) == '00') or (m.group(2) == '02'):
                power = 'on'
            else:
                power = 'off'
            mqtt_send(config['mqtt']['prefix'] + '/cec/' + str(id), power, True)
            return

        # Device Vendor ID
        m = re.search('>> ([0-9a-f])[0-9a-f]:87', message)
        if m:
            id = int(m.group(1), 16)
            power = 'on'
            mqtt_send(config['mqtt']['prefix'] + '/cec/' + str(id), power, True)
            return

        # Report Physical Address
        m = re.search('>> ([0-9a-f])[0-9a-f]:84', message)
        if m:
            id = int(m.group(1), 16)
            power = 'on'
            mqtt_send(config['mqtt']['prefix'] + '/cec/' + str(id), power, True)
            return


def cec_send(cmd, id=None):
    if id is None:
        cec_client.Transmit(cec_client.CommandFromString(cmd))
    else:
        cec_client.Transmit(cec_client.CommandFromString('1%s:%s' % (hex(id)[2:], cmd)))


def ir_listen_thread():
    try:
        while True:
            try:
                code = lirc.nextcode()
            except lirc.NextCodeError:
                code = None
            if code:
                code = code[0]
                mqtt_send(config['mqtt']['prefix'] + '/ir/rx', code)
            else:
                time.sleep(0.2)
    except:
        return


def ir_send(remote, key):
    subprocess.call(["irsend", "SEND_ONCE", remote, key])


def cec_refresh():
    try:
        for id in config['cec']['devices'].split(','):
            cec_send('8F', id=int(id))

    except Exception as e:
        print("Error during refreshing: ", str(e))


def cleanup():
    mqtt_client.loop_stop()
    mqtt_client.disconnect()
    if int(config['ir']['enabled']) == 1:
        lirc.deinit()


try:
    ### Parse config ###
    try:
        Config = ConfigParser.SafeConfigParser()
        if Config.read("config.ini"):

            # Load all sections and overwrite default configuration
            for section in Config.sections():
                config[section].update(dict(Config.items(section)))

        # Environment variables
        for section in config:
            for key, value in config[section].items():
                env = os.getenv(section.upper() + '_' + key.upper());
                if env:
                    config[section][key] = type(value)(env)

        # Do some checks
        if (not int(config['cec']['enabled']) == 1) and \
                (not int(config['ir']['enabled']) == 1):
            raise Exception('IR and CEC are both disabled. Can\'t continue.')

    except Exception as e:
        print("ERROR: Could not configure:", str(e))
        exit(1)

    ### Setup CEC ###
    if int(config['cec']['enabled']) == 1:
        print("Initialising CEC...")
        try:
            import cec

            cec_config = cec.libcec_configuration()
            cec_config.strDeviceName = "cec-ir-mqtt"
            cec_config.bActivateSource = 0
            cec_config.deviceTypes.Add(cec.CEC_DEVICE_TYPE_RECORDING_DEVICE)
            cec_config.clientVersion = cec.LIBCEC_VERSION_CURRENT
            cec_config.SetLogCallback(cec_on_message)
            cec_client = cec.ICECAdapter.Create(cec_config)
            if not cec_client.Open(config['cec']['port']):
                raise Exception("Could not connect to cec adapter")
        except Exception as e:
            print("ERROR: Could not initialise CEC:", str(e))
            exit(1)

    ### Setup IR ###
    if int(config['ir']['enabled']) == 1:
        print("Initialising IR...")
        try:
            import lirc

            lirc.init("cec-ir-mqtt", "lircrc", blocking=False)
            lirc_thread = threading.Thread(target=ir_listen_thread)
            lirc_thread.start()
        except Exception as e:
            print("ERROR: Could not initialise IR:", str(e))
            exit(1)

    ### Setup MQTT ###
    print("Initialising MQTT...")
    mqtt_client = mqtt.Client("cec-ir-mqtt")
    mqtt_client.on_connect = mqtt_on_connect
    mqtt_client.on_message = mqtt_on_message
    if config['mqtt']['user']:
        mqtt_client.username_pw_set(config['mqtt']['user'], password=config['mqtt']['password']);
    mqtt_client.connect(config['mqtt']['broker'], config['mqtt']['port'], 60)
    mqtt_client.loop_start()

    print("Starting main loop...")
    while True:
        if int(config['cec']['enabled']) == 1:
            cec_refresh()
        time.sleep(10)

except KeyboardInterrupt:
    cleanup()

except RuntimeError:
    cleanup()

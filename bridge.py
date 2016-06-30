#!/usr/bin/python2

import paho.mqtt.client as mqtt
import cec
import json
import time

### Settings
mqqt_broker = "rafael"
mqqt_port = 1883
mqqt_prefix = 'cec'
cec_port = 'RPI'


def cec_on_log(level, time, message):
    if level == cec.CEC_LOG_TRAFFIC:
        print "log traf: ", message

    if level == cec.CEC_LOG_ALL:
        print "log all: ", message

    if level == cec.CEC_LOG_DEBUG:
        print "log debug: ", message

    if level == cec.CEC_LOG_NOTICE:
        print "log notice: ", message

    if level == cec.CEC_LOG_WARNING:
        print "log warning: ", message

    if level == cec.CEC_LOG_ERROR:
        print "log error: ", message


def cec_on_key(key, duration):
    print "key: ", key, duration


def cec_on_cmd(level, time, message):
    print "cmd: ", message


def cec_on_menu(level, time, message):
    print "menu: ", message


def cec_on_source(level, time, message):
    print "source: ", message


def mqqt_on_connect(client, userdata, flags, rc):
    """@type client: paho.mqtt.client """
    client.subscribe(mqqt_prefix + '/tx')
    client.subscribe(mqqt_prefix + '/mute')
    client.subscribe(mqqt_prefix + '/unmute')
    client.subscribe(mqqt_prefix + '/volup')
    client.subscribe(mqqt_prefix + '/voldown')
    client.subscribe(mqqt_prefix + '/on')
    client.subscribe(mqqt_prefix + '/off')


def mqqt_on_message(client, userdata, message):
    """@type client: paho.mqtt.client """

    try:

        # Decompose topic
        (null, cmd) = message.topic.split('/')
        print "Command received: %s" % cmd

        if cmd == 'tx':
            commands = message.payload.split(',')
            for command in commands:
                print " Sending raw: %s" % command
                lib.Transmit(lib.CommandFromString(command))

        elif cmd == 'mute':
            print " Sending mute"
            lib.AudioMute()

        elif cmd == 'unmute':
            print " Sending unmute"
            lib.AudioUnmute()

        elif cmd == 'voldown':
            print " Sending volume down"
            lib.VolumeDown()

        elif cmd == 'volup':
            print " Sending volume up"
            lib.VolumeUp()

        elif cmd == 'off':
            print " Sending off"
            lib.StandbyDevices(int(message.payload))

        elif cmd == 'on':
            print " Sending on"
            lib.PowerOnDevices(int(message.payload))

        else:
            print " Unknown command %s" % cmd

    except Exception, e:
        print "Error during processing of message: ", message.topic, message.payload, str(e)


def refresh():
    try:
        print "Refreshing...."
        # lib.AudioStatus()

        # Scan all devices on the bus
        addresses = lib.GetActiveDevices()
        for x in range(15):
            if addresses.IsSet(x):
                power = lib.GetDevicePowerStatus(x)
                mqttc.publish(mqqt_prefix + '/power/' + str(x), lib.PowerStatusToString(power))

    except Exception, e:
        print "Error during refreshing: ", str(e)


def cleanup():
    mqttc.disconnect()


try:

    ### Setup MQTT ###
    mqttc = mqtt.Client("cec-mqtt")
    mqttc.on_connect = mqqt_on_connect
    mqttc.on_message = mqqt_on_message
    mqttc.connect(mqqt_broker, mqqt_port, 60)
    mqttc.loop_start()

    ### Setup CEC ###
    cecconfig = cec.libcec_configuration()
    cecconfig.strDeviceName = "cec-mqtt"
    cecconfig.bActivateSource = 0
    cecconfig.deviceTypes.Add(cec.CEC_DEVICE_TYPE_RECORDING_DEVICE)
    cecconfig.clientVersion = cec.LIBCEC_VERSION_CURRENT
    cecconfig.SetLogCallback(cec_on_log)
    cecconfig.SetKeyPressCallback(cec_on_key)
    cecconfig.SetCommandCallback(cec_on_cmd)
    cecconfig.SetMenuStateCallback(cec_on_menu)
    cecconfig.SetSourceActivatedCallback(cec_on_source)
    lib = cec.ICECAdapter.Create(cecconfig)
    print "libCEC version " + lib.VersionToString(cecconfig.serverVersion)
    print "Library: " + lib.GetLibInfo()

    # Open connection
    if not lib.Open(cec_port):
        print("failed to open a connection to the CEC adapter")
        exit(1)

    while True:
        refresh()
        time.sleep(10)

except (KeyboardInterrupt):
    print "Interrupt received"
    cleanup()

except (RuntimeError):
    print "uh-oh! time to die"
    cleanup()

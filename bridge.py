#!/usr/bin/python2

import paho.mqtt.client as mqtt
#import cec
#import lirc
import subprocess
import time
import re
import ConfigParser
import threading

# Default configuration
config = {
    'mqtt': {
        'broker': 'localhost',
        'port': 1883,
        'prefix': 'media',
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
cache = {}
closing_down = 0


def mqqt_on_connect(client, userdata, flags, rc):
    """@type client: paho.mqtt.client """

    # Subscribe to CEC commands
    if int(config['cec']['enabled']) == 1:
        client.subscribe(config['mqtt']['prefix'] + '/cec/#')

    # Subscribe to IR commands
    if int(config['ir']['enabled']) == 1:
        client.subscribe(config['mqtt']['prefix'] + '/ir/#')


def mqqt_on_message(client, userdata, message):
    """@type client: paho.mqtt.client """

    try:

        # Decode topic
        cmd = message.topic.replace(config['mqtt']['prefix'], '').strip('/')
        print "Command received on topic %s: %s (%s)" % (message.topic, cmd, message.payload)

        if (cmd == 'ir/rx') or (cmd == 'cec/rx'):
            # We should not process these
            return

        elif cmd == 'ir/tx':
            (remote, key) = message.payload.split(',')
            ir_send(remote, key)

        elif cmd == 'cec/tx':
            commands = message.payload.split(',')
            for command in commands:
                print " Sending raw: %s" % command
                cec_send(command)

        elif cmd == 'cec/mute':
            print " Sending mute"
            cec_client.AudioMute()

        elif cmd == 'cec/unmute':
            print " Sending unmute"
            cec_client.AudioUnmute()

        elif cmd == 'cec/voldown':
            print " Sending volume down"
            cec_client.VolumeDown()

        elif cmd == 'cec/volup':
            print " Sending volume up"
            cec_client.VolumeUp()

        elif cmd == 'cec/off':
            print " Sending off"
            id = int(message.payload)
            cec_send('36', id=id)
            mqtt_send(config['mqtt']['prefix'] + '/cec/power/' + str(id), 'standby', True)

        elif cmd == 'cec/on':
            print " Sending on"
            id = int(message.payload)
            cec_send('44:6D', id=id)
            mqtt_send(config['mqtt']['prefix'] + '/cec/power/' + str(id), 'on', True)

        else:
            print " Unknown command %s" % cmd

    except Exception, e:
        print "Error during processing of message: ", \
            message.topic, message.payload, str(e)


def mqtt_send(topic, value, retain=False):
    if not retain or ((topic not in cache) or (cache[topic] != value)):
        cache[topic] = value
        mqtt_client.publish(topic, value, retain=retain)


def cec_on_message(level, time, message):
    print message

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
                power = 'standby'
            mqtt_send(config['mqtt']['prefix'] + '/cec/power/' + str(id), power, True)
            return

        # Device Vendor ID
        m = re.search('>> ([0-9a-f])[0-9a-f]:87', message)
        if m:
            id = int(m.group(1), 16)
            power = 'on'
            mqtt_send(config['mqtt']['prefix'] + '/cec/power/' + str(id), power, True)
            return

        # Report Physical Address
        m = re.search('>> ([0-9a-f])[0-9a-f]:84', message)
        if m:
            id = int(m.group(1), 16)
            power = 'on'
            mqtt_send(config['mqtt']['prefix'] + '/cec/power/' + str(id), power, True)
            return


def cec_send(cmd, id=None):
    if id is None:
        cec_client.Transmit(
            cec_client.CommandFromString(cmd)
        )
    else:
        cec_client.Transmit(
            cec_client.CommandFromString('1%s:%s' % (hex(id)[2:], cmd))
        )


def ir_listen_thread():
    try:
        while True:
            queue = lirc.nextcode()
            if (queue):
                for code in queue:
                    mqtt_send(config['mqtt']['prefix'] + '/ir/rx', code)
            time.sleep(0.1)
    except:
        return


def ir_send(remote, key):
    subprocess.call(["irsend", "SEND_ONCE", remote, key])


def cec_refresh():
    try:
        print "Refreshing...."
        for id in config['cec']['devices'].split(','):
            cec_send('8F', id=int(id))

    except Exception, e:
        print "Error during refreshing: ", str(e)


def cleanup():
    mqtt_client.disconnect()
    if int(config['ir']['enabled']) == 1:
        lirc.deinit()


try:
    ### Parse config ###
    try:
        Config = ConfigParser.SafeConfigParser()
        if not Config.read("config.ini"):
            raise Exception('Could not load config.ini')

        # Load all sections and overwrite default configuration
        for section in Config.sections():
            config[section].update(dict(Config.items(section)))

        # Do some checks
        if (not int(config['cec']['enabled']) == 1) and\
                (not int(config['ir']['enabled']) == 1):
            raise Exception('IR and CEC are both disabled. Can\'t continue.')

    except Exception, e:
        print "ERROR: Could not configure:", str(e)
        exit(1)

    ### Setup MQTT ###
    print "Initialising MQTT..."
    mqtt_client = mqtt.Client("cec-ir-mqtt")
    mqtt_client.on_connect = mqqt_on_connect
    mqtt_client.on_message = mqqt_on_message
    mqtt_client.connect(config['mqtt']['broker'], config['mqtt']['port'], 60)
    mqtt_client.loop_start()

    ### Setup CEC ###
    if int(config['cec']['enabled']) == 1:
        import cec
        print "Initialising CEC..."
        try:
            cec_config = cec.libcec_configuration()
            cec_config.strDeviceName = "cec-ir-mqtt"
            cec_config.bActivateSource = 0
            cec_config.deviceTypes.Add(cec.CEC_DEVICE_TYPE_RECORDING_DEVICE)
            cec_config.clientVersion = cec.LIBCEC_VERSION_CURRENT
            cec_config.SetLogCallback(cec_on_message)
            cec_client = cec.ICECAdapter.Create(cec_config)
            if not cec_client.Open(config['cec']['port']):
                raise Exception("Could not connect to cec adapter")
        except Exception, e:
            print "ERROR: Could not initialise CEC:", str(e)
            exit(1)

    ### Setup IR ###
    if int(config['ir']['enabled']) == 1:
        import lirc
        print "Initialising IR..."
        try:
            lirc.init("cec-ir-mqtt", "lircrc", blocking=False)
            lirc_thread = threading.Thread(target=ir_listen_thread)
            lirc_thread.start()

        except Exception, e:
            print "ERROR: Could not initialise IR:", str(e)
            exit(1)

    print "Starting main loop..."
    while True:
        if int(config['cec']['enabled']) == 1:
            cec_refresh()
        time.sleep(10)

except (KeyboardInterrupt):
    cleanup()

except (RuntimeError):
    cleanup()

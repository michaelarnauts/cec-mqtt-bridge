cec-mqtt-bridge
===============

A HDMI-CEC / IR to MQTT bridge for connecting your AV-devices to your Home Automation system. You can control and monitor
power status and volume.

# Features
* Power control (CEC + IR)
* Power feedback (CEC only)
* Volume control (CEC + IR)
* Raw command / keypress support

# Dependencies

## MQTT (required)
* MQTT broker (like [Mosquitto](https://mosquitto.org/))

## HDMI-CEC (optional)
* libcec3 with python bindings (https://drgeoffathome.wordpress.com/2015/08/09/a-premade-libcec-deb/ for a compiled RPI version)
  * You might need to compile the bindings yourself. See [this home-assistant issue](https://github.com/home-assistant/home-assistant/issues/2306) for more information.
* HDMI-CEC interface device (like a [Pulse-Eight](https://www.pulse-eight.com/) device, or a Raspberry Pi)

## IR (optional)
* lirc + hardware to receive and send IR signals
* python-lirc (https://pypi.python.org/pypi/python-lirc/)


# MQTT Topics

The bridge subscribes to the following topics:

| topic              | body         | remark |
|:-------------------|--------------|--------|
| media/cec/on       | `id`         | Turn on device with id `id`. |
| media/cec/off      | `id`         | Turn off device with id `id`. |
| media/cec/mute     |              | Mute the audio. |
| media/cec/unmute   |              | Unmute the audio. |
| media/cec/volup    |              | Turn the volume up. |
| media/cec/voldown  |              | Turn the volume down. |
| media/cec/tx       | `commands`   | Send the specified `commands` to the CEC bus. You can specify multiple commands by seperating that with a space. Example: `cec/tx 15:44:41,15:45`. |
| media/ir/tx        | `remote,key` | Send the specified `key` of `remote` to the IR transmitter. |

The bridge publishes to the following topics:

| topic                | body          | remark |
|:---------------------|---------------|--------|
| media/cec/power/`id` | `status`      | Report power status `status` of `id`. |
| media/cec/rx         | `command`     | Notify that `command` was received. |
| media/ir/rx          | `remote,key`  | Notify that `key` of `remote` was detected. |

`id` is the address (0-15) of the device on the CEC-bus.

# Examples
* `mosquitto_pub -t media/cec/volup -m ''`
* `mosquitto_pub -t media/cec/tx -m '15:44:42,15:45'`

# Interesting links
* https://github.com/nvella/mqtt-cec
* http://www.cec-o-matic.com/
* http://wiki.kwikwai.com/index.php?title=The_HDMI-CEC_bus
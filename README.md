cec-mqtt-bridge
===============

A HDMI-CEC to MQTT bridge for connecting HDMI-CEC-devices to your Home Automation system. You can control and monitor
power status and volume.

# Requirements
* MQTT broker (like [Mosquitto](https://mosquitto.org/))
* HDMI-CEC interface device (like a [Pulse-Eight](https://www.pulse-eight.com/) device, or a Raspberry Pi)
* HDMI-CEC compatible devices (TV, audio receiver, cable box, ...)

# Features
* Power control
* Volume control
* Raw command support
* Power feedback

# MQTT Topics

The bridge subscribes to the following topics:

| topic       | body       | remark |
|:------------|------------|--------|
| cec/on      | `id`       | Turn on device with id `id`. |
| cec/off     | `id`       | Turn off device with id `id`. |
| cec/mute    |            | Mute the audio. |
| cec/unmute  |            | Unmute the audio. |
| cec/volup   |            | Turn the volume up. |
| cec/voldown |            | Turn the volume down. |
| cec/tx      | `commands` | Send the specified `commands` to the CEC bus. You can specify multiple commands by seperating that with a space. Example: `cec/tx 15:44:41,15:45`. |

The bridge publishes to the following topics:

| topic          | body      | remark |
|:---------------|-----------|--------|
| cec/power/`id` | `status`  | Report power status `status` of `id`. |

`id` is the address (0-15) of the device on the CEC-bus.

# Examples
* `mosquitto_pub -t cec/volup -m ''`
* `mosquitto_pub -t cec/tx -m '15:44:42,15:45'`

# Interesting links
* https://github.com/nvella/mqtt-cec
* http://www.cec-o-matic.com/
* http://wiki.kwikwai.com/index.php?title=The_HDMI-CEC_bus
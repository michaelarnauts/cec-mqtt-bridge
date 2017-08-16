cec-mqtt-bridge
===============

A HDMI-CEC / IR to MQTT bridge written in Python 3 for connecting your AV-devices to your Home Automation system. You can control and monitor power status and volume.

# Features
* CEC
  * Power control
  * Volume control
  * Power feedback
  * Relay CEC messages from HDMI to broker (RX)
  * Relay CEC messages from broker to HDMI (TX)
* IR
  * Relay IR keypresses from IR to broker (RX)
  * Relay IR keypresses from broker to IR (TX)

# Dependencies

## MQTT (required)
* MQTT broker (like [Mosquitto](https://mosquitto.org/))

## HDMI-CEC (optional)
* libcec4 with python bindings (https://github.com/Pulse-Eight/libcec)
  * You can compile the bindings yourself, or use precompiled packages from my [libcec directory](libcec/).
* HDMI-CEC interface device (like a [Pulse-Eight](https://www.pulse-eight.com/) device, or a Raspberry Pi)

## IR (optional)
* lirc + hardware to receive and send IR signals
* python-lirc (https://pypi.python.org/pypi/python-lirc/)

# MQTT Topics

The bridge subscribes to the following topics:

| topic                   | body                                    | remark                                           |
|:------------------------|-----------------------------------------|--------------------------------------------------|
| `prefix`/cec/`id`/cmd   | `on` / `off`                            | Turn on/off device with id `id`.                 |
| `prefix`/cec/cmd        | `mute` / `unmute` / `voldown` / `volup` | Sends the specified command to the audio system. |
| `prefix`/cec/tx         | `commands`                              | Send the specified `commands` to the CEC bus. You can specify multiple commands by separating them with a space. Example: `cec/tx 15:44:41,15:45`. |
| `prefix`/ir/`remote`/tx | `key`                                   | Send the specified `key` of `remote` to the IR transmitter. |

The bridge publishes to the following topics:

| topic                   | body                                    | remark                                           |
|:------------------------|-----------------------------------------|--------------------------------------------------|
| `prefix`/cec/`id`       | `on` / `off`                            | Report power status of device with id `id`.      |
| `prefix`/cec/rx         | `command`                               | Notify that `command` was received.              |
| `prefix`/ir/rx          | `key`                                   | Notify that `key` of `remote` was received. You have to configure `key` in the lircrc file. |

`id` is the address (0-15) of the device on the CEC-bus.

# Examples
* `mosquitto_pub -t media/cec/volup -m ''`
* `mosquitto_pub -t media/cec/tx -m '15:44:42,15:45'`

# Interesting links
* https://github.com/nvella/mqtt-cec
* http://www.cec-o-matic.com/
* http://wiki.kwikwai.com/index.php?title=The_HDMI-CEC_bus

#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import logging
import threading
import time

LOGGER = logging.getLogger(__name__)

DEFAULT_CONFIGURATION = {
    'enabled': 0,
}


class Lirc:

    def __init__(self, mqtt_send):
        # self._config = config
        self._mqtt_send = mqtt_send

        logging.info("Initialising IR...")
        try:
            import lirc

            lirc.init("cec-ir-mqtt", "lircrc", blocking=False)
            lirc_thread = threading.Thread(target=ir_listen_thread)
            lirc_thread.start()
        except Exception as e:
            logging.error("Could not initialise IR:", str(e))
            exit(1)

    def ir_listen_thread():
        try:
            while True:
                try:
                    code = lirc.nextcode()
                except lirc.NextCodeError:
                    code = None
                if code:
                    code = code[0].split(",", maxsplit=1)
                    if len(code) == 1:
                        mqtt_send('ir/rx', code[0].strip())
                    elif len(code) == 2:
                        remote = code[0].strip()
                        code = code[1].strip()
                        mqtt_send('ir/' + remote + '/rx', code)
                else:
                    time.sleep(0.2)
        except:
            return

    def ir_send(remote, key):
        subprocess.call(["irsend", "SEND_ONCE", remote, key])

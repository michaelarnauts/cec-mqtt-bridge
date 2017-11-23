#!/usr/bin/env python3

import sys
import re

PROGNAME = "cec-ir-mqtt"

TEMPLATE = """
begin
  remote = {remote}
  button = {key}
  prog = {prog}
  config = {remote},{key}
end
"""


class Remote(object):
    def __init__(self, name):
        self.name = name
        self.keys = []

    def add_key(self, keyname):
        self.keys.append(keyname)


class Parser(object):
    def __init__(self):
        self.remotes = []

    def _parse_toplevel(self, line: str):
        if re.match("^[ \t]*begin[ ]+remote.*", line):
            return self._parse_remote
        return self._parse_toplevel

    def _parse_remote(self, line: str):
        if re.match("^[ \t]*begin[ ]+codes.*", line):
            return self._parse_keys
        if re.match("^[ \t]*end[ ]+remote.*", line):
            return self._parse_toplevel

        match = re.match("^[ \t]*name[ \t]+(?P<name>[^ \t]+)([ \t].*)?$", line)
        if match is not None:
            self.remotes.append(Remote(match.group("name")))

        return self._parse_remote

    def _parse_keys(self, line: str):
        if re.match("^[ \t]*end[ ]+codes.*", line):
            return self._parse_remote

        match = re.match("^[ \t]*(?P<KEY>[^ \t]+)[ \t]+(?P<CODE>0x[^ \t]+)([ \t].*)?$", line)
        if match is not None:
            self.remotes[-1].add_key(match.group("KEY"))

        return self._parse_keys

    def parse_file(self, filename):
        parser = self._parse_toplevel

        with open(filename, "r") as fn:
            for line in fn.readlines():
                line = line.strip()
                if line.startswith("#"):
                    continue
                parser = parser(line)

    def print(self):
        for remote in self.remotes:
            for key in remote.keys:
                block = TEMPLATE.format(prog=PROGNAME, remote=remote.name, key=key)
                print(block)


if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("Usage: ./create_lircrc.py <lircd-cfg>")
        sys.exit(1)

    parser = Parser()
    parser.parse_file(sys.argv[1])
    parser.print()

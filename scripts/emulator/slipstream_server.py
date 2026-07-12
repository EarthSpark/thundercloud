#!/usr/bin/env python

"""Slipstream server emulator."""

import argparse
import json
import logging
import random
import sys
import time

from microgrid import MicrogridEmulator
from twisted.internet import protocol, reactor

HOST = "127.0.0.1"
PORT = 4000
logger = logging.getLogger(__name__)


class SlipstreamJsonProtocol(protocol.Protocol):
    """Protocol for handling incoming slipstream json packets."""

    def dataReceived(self, data):
        """Handle and respond to incoming data."""
        # self.request is the TCP socket connected to the client
        logger.debug("start request")

        try:
            json_data = json.loads(data)
        except:
            logger.debug("start of data\n%s\nend of data" % (data,))
            raise
        logger.debug(json_data)

        # random delay in response
        delay = random.randint(0, 3) + 0.1
        logger.debug("sleeping for %f" % (delay,))
        time.sleep(delay)

        # parse json data to figure out what kind of request this is.
        try:
            response_packet = self.factory.microgrid.gateway.get_pkt(json_data)
            response = json.dumps(response_packet)
            logger.debug(response)
            self.transport.write(response + "\n")
        except Exception as e:
            logger.debug("no response received from microgrid: %r" % (e,))
            pass

        logger.debug("end request\n\n\n")

        time.sleep(0.1)


class SlipstreamJsonProtocolFactory(protocol.Factory):
    """Slipsteam Protocol Factory."""

    # This will be used by the default buildProtocol to create new protocols:
    protocol = SlipstreamJsonProtocol

    def __init__(self, microgrid):
        """Init the factory with a microgrid emulator object."""
        self.microgrid = microgrid


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Microgrid Emulator")
    parser.add_argument(
        "--config",
        dest="config",
        nargs="?",
        type=argparse.FileType("r"),
        default=sys.stdin,
        help="config file to create grid from",
    )

    args = parser.parse_args()

    cfg = json.load(args.config)

    m = MicrogridEmulator(cfg)

    factory = SlipstreamJsonProtocolFactory(m)
    reactor.listenTCP(PORT, factory)
    reactor.run()

"""Microgrid Emulator Module."""

from __future__ import print_function

import calendar
import collections.abc
import datetime
import json
import random


# copied from jsonpacket.py
def update(orig_dict, new_dict):
    """Utility to recursively merge dictionaries, modifying original."""
    if orig_dict == new_dict:
        return orig_dict

    for key, val in new_dict.items():
        if isinstance(val, collections.abc.Mapping):
            tmp = update(orig_dict.get(key, {}), val)
            orig_dict[key] = tmp
        elif isinstance(val, list):
            orig_dict.setdefault(key, [])
            orig_dict[key] = orig_dict[key] + val
        else:
            orig_dict[key] = new_dict[key]
    return orig_dict


class MeterEmulator(object):
    """Meter emulator."""

    def __init__(self, mac, config):
        """Init the meter with a mac address and config dict."""
        self.config = config
        self.mac = mac
        self.uptime_datetime = datetime.datetime.utcnow()
        self.last_heartbeat_timestamp = 0
        self.next_heartbeat_timestamp = 0
        self.last_heartbeat_data = {}
        print("generating emulated meter mac: %s" % self.mac)

    def get_value(self, field):
        """Get a config value."""
        data = self.config[field]
        # make a random value between min and max
        if isinstance(data, dict) and "min" in data and "max" in data:
            return random.uniform(data["min"], data["max"])
        # just return the value
        return data

    def _set_value(self, field, value):
        """Set a config value."""
        print("setting %s to %s" % (field, value))
        self.config[field] = value

    def process_command(self, cmd):
        """Set the saved state of a meter."""
        if cmd == "enable":
            state = "on"
        elif cmd == "disable":
            state = "off"
        else:
            print("uncrecognized update command: %s" % (cmd))
            return

        self._set_value("state", state)

    def process_sm15r_set_config_packet(self, request_json):
        """Process SM15R_SET_CONFIG packets sent to the meter, return an ack."""
        response_packet = self.make_base_network_packet(request_json)
        payload = request_json["application_packet"]
        del payload["type"]

        """
        "command": "enable/disable",
        "power_limit": 30,
        "soft_power_limit": 45,
        "throttle_on_time": 2,
        "throttle_off_time": 10,
        "current_limit": 5,
        "device_type": "meter"
        """

        for k, v in payload.items():
            self._set_value(k, v)

        self.process_command(payload["command"])

        response_packet["application_packet"] = {
            "application_version": "9389D60DAE",
            "bootloader_version": "0000000000",
            "type": "SM15R_SET_CONFIG_REPLY",
        }
        return response_packet

    def process_sm15r_read_packet(self, request_json):
        """Process SM15R_READ packets sent to the meter, return a SM15R_READ_REPLY."""
        response_packet = self.make_base_network_packet(request_json)
        response_packet["application_packet"] = {"type": "SM15R_READ_REPLY"}
        response_packet["application_packet"].update(self.last_heartbeat_data)
        return response_packet

    def generate_heartbeat_data(self, start_timestamp, end_timestamp):
        """Generate meter reading data for a heartbeat period."""
        voltage_avg = self.get_value("voltage_avg")
        current_avg = self.get_value("current_avg")

        uptime = (datetime.datetime.utcnow() - self.uptime_datetime).total_seconds()
        self._set_value("uptime", uptime)

        energy = self.get_value("energy")
        energy += random.randint(1, 10)
        self._set_value("energy", energy)

        data = {
            "state": self.get_value("state"),
            "uptime": self.get_value("uptime"),
            "heartbeat_start": start_timestamp,
            "heartbeat_end": end_timestamp,
            "frequency": self.get_value("frequency"),
            "voltage_min": voltage_avg - random.randint(1, 5),
            "voltage_max": voltage_avg + random.randint(1, 5),
            "voltage_avg": voltage_avg,
            "current_min": current_avg - random.randint(0, 1),
            "current_max": current_avg + random.randint(1, 5),
            "current_avg": current_avg,
            "energy": energy,
            "true_power_inst": self.get_value("true_power_inst"),
            "true_power_avg": self.get_value("true_power_avg"),
            "apparent_power_avg": self.get_value("apparent_power_avg"),
            "power_factor_avg": self.get_value("power_factor_avg"),
            "user_power_limit": self.get_value("soft_power_limit"),  # is this the right power limit?
        }
        return data

    def update_local_heartbeat_timestamp(self, request_json):
        """The heartbeat changed, modify our saved version."""
        if self.next_heartbeat_timestamp != request_json["heartbeat_timestamp"]:
            # heartbeat occurred
            # save a copy of the data from the last heartbeat
            self.last_heartbeat_data = self.generate_heartbeat_data(
                start_timestamp=self.last_heartbeat_timestamp,
                end_timestamp=self.next_heartbeat_timestamp,
            )
            # update the heartbeat timestamps
            self.last_heartbeat_timestamp = self.next_heartbeat_timestamp
            self.next_heartbeat_timestamp = request_json["heartbeat_timestamp"]

    def get_meter_pkt(self, request_json):
        """Get the response packet for a given request."""
        # dont transmit if the rand is above my tx %
        if "tx" in self.config and self.config["tx"] < random.random():
            return

        print("handling packet for meter %s" % self.mac)

        self.update_local_heartbeat_timestamp(request_json)

        router = {
            "SM15R_SET_CONFIG": self.process_sm15r_set_config_packet,
            "SM15R_READ": self.process_sm15r_read_packet,
        }

        packet_type = request_json["application_packet"]["type"]
        handler = router.get(packet_type, None)
        if handler:
            return handler(request_json)

    def make_base_network_packet(self, request_json):
        """Generate the base packet for a given request."""
        response_packet = request_json.copy()
        response_packet["application_packet"] = {}
        response_packet["ttl"] = (random.randint(0, request_json["ttl"] - 1),)
        # swap source and destination
        response_packet["src_address"] = request_json["dst_address"]
        response_packet["dst_address"] = request_json["src_address"]
        return response_packet


class GatewayEmulator(object):
    """Gateway emulator."""

    def __init__(self, microgrid):
        """Init the Gateway with a microgrid object."""
        self.microgrid = microgrid
        self.heartbeat_timestamp = calendar.timegm(datetime.datetime.utcnow().utctimetuple())
        self.seq_num = 0

    def process_gateway_packet(self, request_json):
        """Process config packets sent to the gateway, return an ack."""
        if request_json["slipstream_pkt_type"] == "SLIPSTREAM_PKT_TYPE_SET_HEARTBEAT":
            print("got gateway config request")
            next_heartbeat_timestamp = request_json["heartbeat_timestamp"]
            print("updating heartbeat from %s to %s" % (self.heartbeat_timestamp, next_heartbeat_timestamp))
            self.heartbeat_timestamp = next_heartbeat_timestamp

            response_packet = {
                "protocol_version": 1,
                "heartbeat_timestamp": self.heartbeat_timestamp,
                "slipstream_pkt_type": "SET_HEARTBEAT_REPLY",
                "type": "JSON_PKT_TYPE_SLIPSTREAM",
            }

            return response_packet
        raise Exception("got unknown slipstream_pkt_type")

    def get_seq_num(self):
        """Increment and return the seq_num."""
        self.seq_num += 1
        if self.seq_num == 128:
            self.seq_num = 0
        return self.seq_num

    def get_pkt(self, request_json):
        """Get the right packet for a given request."""
        if request_json["type"] == "JSON_PKT_TYPE_SLIPSTREAM":
            return self.process_gateway_packet(request_json)

        elif request_json["type"] == "JSON_PKT_TYPE_SPARKMAC":
            # this packet is destined for the network, need to inject the heartbeat and gateway timestamp
            request_json["heartbeat_timestamp"] = self.heartbeat_timestamp
            request_json["timestamp_sec"] = calendar.timegm(datetime.datetime.utcnow().utctimetuple())
            request_json["timestamp_ms"] = random.randint(1, 100)
            request_json["seq_num"] = self.get_seq_num()

            mac = request_json.get("dst_address", None)
            if mac is not None:
                if mac not in self.microgrid.nodes:
                    raise Exception("unknown meter")

                response = self.microgrid.nodes[mac].get_meter_pkt(request_json)
                if response:
                    response["hops"] = self.microgrid.random_topology(request_json["forwarding"])
                    return response
                raise Exception("no response")

        raise Exception("got unknown packet type")


class MicrogridEmulator(object):
    """Microgrid Emulator."""

    raw_config = None
    nodes = {}

    def __init__(self, raw_config):
        """Init the microgrid with the config file."""
        self.raw_config = raw_config
        self.parse_devices()
        self.gateway = GatewayEmulator(microgrid=self)

    def parse_devices(self):
        """Generate devices from the config."""
        for device_type, device_config in self.raw_config["devices"].items():
            if device_type == "SM15R":
                for did in device_config["ids"]:
                    self.nodes[did] = MeterEmulator(did, self.get_config(device_config["config"], str(did)))
            else:
                print("unknown device type in config %s" % device_type)

    def get_config(self, base_config, mac):
        """Recursively process the config file."""
        # recursively get the config data for a mac
        # if a mac contains a base, import the base first
        # if no base is defined, import default first
        # resolution order is mac, base, ... base, default
        config = {}
        if mac in base_config and mac != "default":
            base = base_config[mac].get("base", "default")
            update(config, self.get_config(base_config, mac=base))
            update(config, base_config[mac])
            return config
        update(config, base_config["default"])
        return config

    def random_topology(self, route=None):
        """Generate random topology data for the response packet."""
        # FIXME: use a graph and generate somewhat realistic routes
        topology = []

        if "route" in route:
            for mac in route["route"]:
                topology.append(
                    {"last_hop": mac, "rssi": random.randint(1, 32) * -1, "retry": random.randint(1, 10)}
                )

            route["route"].pop(-1)
            reverse_route = reversed(route["route"])

            for mac in reverse_route:
                topology.append(
                    {"last_hop": mac, "rssi": random.randint(1, 32) * -1, "retry": random.randint(1, 10)}
                )
        else:
            route_len = random.randint(1, 5)
            route = random.sample(xrange(64), route_len)
            route += reversed(route[1:])
            for mac in route:
                topology.append(
                    {"last_hop": mac, "rssi": random.randint(1, 32) * -1, "retry": random.randint(1, 10)}
                )

        return topology


if __name__ == "__main__":
    config = """
        {
            "devices": {
                "SM15R": {
                    "ids": [1, 2, 3, 4],
                    "config": {
                        "default": {
                            "state": true,
                            "uptime": 0,
                            "heartbeat_timestamp": 0,
                            "frequency": {
                                "min": 61,
                                "max": 64
                            },
                            "voltage_avg": {
                                "min": 112,
                                "max": 126
                            },
                            "user_power_limit": 11,
                            "tx": 0.9
                        }
                    }
                }
            }
        }
    """

    cfg = json.loads(config)
    g = MicrogridEmulator(cfg)

    print(g)

# -*- coding: utf-8 -*-

# FOGLAMP_BEGIN
# See: https://foglamp-foglamp-documentation.readthedocs-hosted.com
# FOGLAMP_END

""" InfluxDBCloud North plugin"""

import asyncio
import json

from foglamp.common import logger
from foglamp.plugins.north.common.common import *
from influxdb_client import InfluxDBClient
from influxdb_client.client.write_api import SYNCHRONOUS

__author__ = "Mark Riddoch"
__copyright__ = "Copyright (c) 2020 Dianomic Systems"
__license__ = "Apache 2.0"
__version__ = "${VERSION}"

_LOGGER = logger.setup(__name__)


influxdbcloud_north = None
config = ""

_DEFAULT_CONFIG = {
    'plugin': {
         'description': 'InfluxDB Cloud North Plugin',
         'type': 'string',
         'default': 'influxdbcloud',
         'readonly': 'true'
    },
    'url': {
        'description': 'Destination URL',
        'type': 'string',
        'default': 'https://eu-central-1-1.aws.cloud2.influxdata.com',
        'order': '1',
        'displayName': 'URL'
    },
    "source": {
         "description": "Source of data to be sent on the stream. May be either readings or statistics.",
         "type": "enumeration",
         "default": "readings",
         "options": ["readings", "statistics"],
         'order': '7',
         'displayName': 'Source'
    },
    "token": {
        "description": "InfluxDB Cloud security token",
        "type": "string",
        "default": "",
        'order': '3',
        'displayName': 'InfluxDB token'
    },
    "org": {
        "description": "Organisation ID within the InfluxDB Cloud",
        "type": "string",
        "default": "",
        'order': '4',
        'displayName': 'Organisation ID'
    },
    "bucket": {
        "description": "Influx Bucket",
        "type": "string",
        "default": "",
        'order': '5',
        'displayName': 'Bucket'
    },
    "measurement": {
        "description": "Measurement name to use in Influx",
        "type": "string",
        "default": "foglamp",
        'order': '6',
        'displayName': 'Measurement'
    }
}


def plugin_info():
    return {
        'name': 'influxdbcloud',
        'version': '2.0.1',
        'type': 'north',
        'interface': '1.0',
        'config': _DEFAULT_CONFIG
    }


def plugin_init(data):
    global influxdbcloud_north, config
    config = data
    influxdbcloud_north = InfluxDBcloudPlugin(config["url"]["value"],config["token"]["value"])
    return config


async def plugin_send(data, payload, stream_id):
    try:
        is_data_sent, new_last_object_id, num_sent = await influxdbcloud_north.send_payloads(payload)
    except asyncio.CancelledError:
        pass
    else:
        return is_data_sent, new_last_object_id, num_sent


def plugin_shutdown(data):
    pass


class InfluxDBcloudPlugin(object):
    """ North InfluxDBcloud Plugin """

    def __init__(self, url, token):
        self.client = InfluxDBClient(url=url, token=token, org=config["org"]["value"])
        self.event_loop = asyncio.get_event_loop()

    async def send_payloads(self, payloads):
        is_data_sent = False
        last_object_id = 0
        num_sent = 0
        try:
            write_api = self.client.write_api(write_options=SYNCHRONOUS)
            measurement = config["measurement"]["value"]
            payload_block = list()
            for p in payloads:
                last_object_id = p["id"]
                readings = p["reading"]
                fp = { "measurement" : measurement,
                        "tags" : {
                            "asset" : p["asset_code"]
                            },
                        "fields" : readings,
                        "time" : p["user_ts"]
                      }
                payload_block.append(fp)
                num_sent = num_sent + 1

            write_api.write(config["bucket"]["value"], config["org"]["value"], payload_block)
            is_data_sent = True
        except Exception as ex:
            _LOGGER.exception("Data could not be sent, %s", str(ex))

        return is_data_sent, last_object_id, num_sent

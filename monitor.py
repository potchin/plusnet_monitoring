#!/bin/python3

# Script for monitoring dsl stats from a plusnet hub 2 and posting to influxdb
# It pulls data from the /nonAuth/wan_conn.xml which doesnt require authentication

import os
import sys
import xml.etree.ElementTree as ET
import requests
from time import sleep
from datetime import datetime
from urllib.parse import unquote
from pprint import pprint
from influxdb import InfluxDBClient

# Grab some config from the environment
router_ip = os.getenv("ROUTER_IP", "192.168.1.254")
influx_host = os.getenv("INFLUX_HOST")
influx_port = os.getenv("INFLUX_PORT", 8086)
influx_user = os.getenv("INFLUX_USER", "root")
influx_pass = os.getenv("INFLUX_PASS", "root")
influx_db = os.getenv("INFLUX_DB", "routerstats")
report_interval = int(os.getenv("REPORT_INTERVAL", 0))


def parseArray(valuestr):
    # print(valuestr)
    valuestr = valuestr.replace(", null", "")
    valuestr = valuestr.replace("[", "")
    valuestr = valuestr.replace("]", "")
    valuestr = valuestr.replace("'", "")
    valuestr = valuestr.replace("\n", "")
    out = []
    for i in valuestr.split(","):
        # print(i)
        if ";" in i:
            j = i.split(";")
            # print(j)
            out.append(j)
        else:
            out.append(i)

    return out


def get_data_from_router():
    r = requests.get(f"http://{router_ip}/nonAuth/wan_conn.xml")
    r.raise_for_status()

    root = ET.fromstring(r.content)

    output_data = {}

    for child in root:
        key = child.tag
        datatype = child.attrib["type"] if "type" in child.attrib.keys() else None
        valuestr = child.attrib["value"]
        valuestr = unquote(valuestr)

        if key == "wan_linestatus_rate_list":
            data = parseArray(valuestr)
            output_data[key] = {}
            output_data[key]["state"] = data[0]
            output_data[key]["mode"] = data[1]
            output_data[key]["mod_type"] = data[2]
            output_data[key]["snr_margin_down"] = int(data[3])
            output_data[key]["snr_margin_up"] = int(data[4])
            output_data[key]["latn_down"] = int(data[5])
            output_data[key]["latn_up"] = int(data[6])
            output_data[key]["satn_down"] = int(data[7])
            output_data[key]["satn_up"] = int(data[8])
            output_data[key]["output_power_down"] = int(data[9])
            output_data[key]["output_power_up"] = int(data[10])
            output_data[key]["rate_down"] = int(data[11])
            output_data[key]["rate_up"] = int(data[12])
            output_data[key]["attainable_rate_down"] = int(int(data[13]) / 1000)
            output_data[key]["attainable_rate_up"] = int(int(data[14]) / 1000)
            output_data[key]["chantype"] = data[15]

        elif key == "status_rate":
            data = parseArray(valuestr)
            output_data[key] = {}
            output_data[key]["rate_up"] = data[0]
            output_data[key]["rate_down"] = data[1]
            output_data[key]["unknown1"] = data[2]
            # output[key]['unknown2'] = data[3]

        elif key == "wan_conn_status_list":
            data = parseArray(valuestr)
            output_data[key] = {}
            output_data[key]["connected"] = data[0]
            output_data[key]["connected_at"] = data[1]
            output_data[key]["unknown1"] = data[2]

        elif key == "wan_conn_volume_list":
            data = parseArray(valuestr)
            output_data[key] = {}
            output_data[key]["unknown1"] = data[0]
            output_data[key]["Downloaded"] = data[1]
            output_data[key]["Uploaded"] = data[2]

        elif datatype == "array":
            output_data[key] = parseArray(valuestr)

        elif ";" in valuestr:
            output_data[key] = valuestr.split(";")
        else:
            output_data[key] = valuestr

    return output_data


def send_to_influx(output_data):
    json_body = []

    for key in output_data["wan_linestatus_rate_list"].keys():
        value = output_data["wan_linestatus_rate_list"][key]

        # strings are pointless
        if isinstance(value, str):
            continue

        json_body.append(
            {
                "measurement": key,
                "tags": {
                    "host": router_ip,
                },
                "time": datetime.utcnow(),
                "fields": {"value": value},
            }
        )

    # pprint(json_body)
    client = InfluxDBClient(
        influx_host, influx_port, influx_user, influx_pass, influx_db
    )

    return client.write_points(json_body)


def main():
    output_data = get_data_from_router()
    if not send_to_influx(output_data):
        sys.exit(1)


if __name__ == "__main__":
    if report_interval > 0:
        while True:
            main()
            sleep(report_interval)
    else:
        main()

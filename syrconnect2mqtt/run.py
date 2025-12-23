import json
import time
import logging

from syr.api import SYRClient
from syr.mqttclient import MQTTClient

logging.basicConfig(level=logging.INFO)
_LOGGER = logging.getLogger("syrconnect2mqtt")


def load_options():
    with open("/data/options.json", "r", encoding="utf-8") as f:
        return json.load(f)


def main():
    opts = load_options()
    username = opts.get("username")
    password = opts.get("password")
    mqtt_host = opts.get("mqtt_host", "core-mosquitto")
    mqtt_port = int(opts.get("mqtt_port", 1883))
    interval = int(opts.get("interval", 60))

    if not username or not password:
        _LOGGER.error("Bitte username und password in den Add-on-Optionen setzen.")
        time.sleep(300)
        return

    api = SYRClient(username, password, logger=_LOGGER)
    mqtt = MQTTClient(mqtt_host, mqtt_port)

    _LOGGER.info("Login bei SYR Connect...")
    projects = api.login_and_get_projects()
    if not projects:
        _LOGGER.error("Keine Projekte gefunden.")
        time.sleep(300)
        return

    project = projects[0]
    project_id = project["id"]
    _LOGGER.info(f"Verwende Projekt: {project_id} ({project['name']})")

    devices = api.get_devices_for_project(project_id)
    if not devices:
        _LOGGER.error("Keine Geräte im Projekt gefunden.")
        time.sleep(300)
        return

    device = devices[0]
    device_id = device["id"]
    _LOGGER.info(f"Verwende Gerät: {device_id} ({device['name']})")

    base_topic = f"syr/{project_id}/{device_id}"

    while True:
        try:
            status = api.get_device_status(project_id, device_id)
            mqtt.publish(f"{base_topic}/status", status)

            stats = api.get_statistics(project_id, device_id)
            mqtt.publish(f"{base_topic}/statistics", stats)

            _LOGGER.info("SYR Daten aktualisiert und via MQTT gesendet.")
        except Exception as e:
            _LOGGER.error(f"Fehler beim Aktualisieren: {e}")

        time.sleep(interval)


if __name__ == "__main__":
    main()

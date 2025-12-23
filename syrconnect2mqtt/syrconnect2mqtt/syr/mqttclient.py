import paho.mqtt.client as mqtt
import json
import logging

_LOGGER = logging.getLogger("syrconnect2mqtt.mqtt")


class MQTTClient:
    def __init__(self, host: str, port: int) -> None:
        self.client = mqtt.Client()
        self.client.connect(host, port, 60)

    def publish(self, topic: str, payload):
        if not isinstance(payload, str):
            payload = json.dumps(payload, ensure_ascii=False)
        _LOGGER.debug("MQTT publish %s: %s", topic, payload)
        self.client.publish(topic, payload, qos=0, retain=True)
        self.client.loop(0.1)

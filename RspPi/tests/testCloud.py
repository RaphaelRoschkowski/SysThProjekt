from azure.iot.device import IoTHubDeviceClient, Message
import json, time

CONNECTION_STRING = ""
client = IoTHubDeviceClient.create_from_connection_string(CONNECTION_STRING)
client.connect()

msg = Message(json.dumps({"value": 12.3, "ts": time.time()}))
client.send_message(msg)
print("Message sent!")
client.disconnect()
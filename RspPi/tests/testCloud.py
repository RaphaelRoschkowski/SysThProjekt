from azure.iot.device import IoTHubDeviceClient, Message
import json, time

CONNECTION_STRING = "HostName=SystemtechnikHub.azure-devices.net;DeviceId=DeskPC;SharedAccessKey=bNlfz9nqP4gA62mvGp/H4nvFoDN7m7LjNl+Md9nqfFM="
client = IoTHubDeviceClient.create_from_connection_string(CONNECTION_STRING)
client.connect()

msg = Message(json.dumps({"value": 12.3, "ts": time.time()}))
client.send_message(msg)
print("Message sent!")
client.disconnect()
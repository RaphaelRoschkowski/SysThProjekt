import paho.mqtt.client as mqtt
import json

def on_message(client,userdata,msg):
    if msg.topic == "wallbox/data":
        data = json.loads(msg.payload.decode())
        print(f"val={data['val']} ts={data['ts']}")
    else:
        print(f"{msg.topic}: {msg.payload.decode()}")

client = mqtt.Client()
client.username_pw_set("blueberry", "blueberry")
client.on_message = on_message
client.connect("192.168.4.2", 1883)
client.subscribe("wallbox/relay/status")
client.subscribe("wallbox/data")
client.publish("wallbox/relay/cmd", "OFF")
client.loop_forever()
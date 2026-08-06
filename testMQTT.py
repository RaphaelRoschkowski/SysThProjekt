import paho.mqtt.client as mqtt

def on_message(client,userdata,msg):
    print(f"{msg.topic}: {msg.payload.decode()}")

client = mqtt.Client()
client.username_pw_set("blueberry", "blueberry")
client.on_message = on_message
client.connect("192.168.4.2", 1883)
client.subscribe("wallbox/relay/status")

client.publish("wallbox/relay/cmd", "ON")
client.loop_forever()
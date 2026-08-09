import paho.mqtt.client as mqtt
import json
import time

def on_message(client,userdata,msg):
    if msg.topic == "wallbox/data":
        data = json.loads(msg.payload.decode())
        print(f"val={data['val']} ts={data['ts']}")
    else:
        print(f"{msg.topic}: {msg.payload.decode()}")
def on_connect(client, userdata, flags, reason_code, properties=None):
    print("Connected; RC:", reason_code)
    client.subscribe("wallbox/relay/status")
    client.subscribe("wallbox/data")
def on_connect_fail(client):
    print("Could not connect")
    #start = time.time()
    #while(time.time()-start <= 3):
    #    pass
    #client.connect("192.168.4.2", 1883)
#setup
client = mqtt.Client()
client.username_pw_set("blueberry", "blueberry")
client.on_message = on_message
client.on_connect = on_connect
client.on_connect_fail = on_connect_fail

#code
client.connect("192.168.4.2", 1883)
client.publish("wallbox/relay/cmd", "OFF")
client.loop_forever()
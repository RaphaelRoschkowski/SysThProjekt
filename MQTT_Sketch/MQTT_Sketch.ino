#include <WiFi.h>
#include <PubSubClient.h>

const char* ap_ssid = "ESP32_IOT";
const char* ap_password = "12345678";

//const uint8_t pi_mac[6] = {0x88, 0xA2, 0x9E, 0xB1, 0x52, 0x74} 
const char* mqtt_server = "192.168.4.2"; // Pi's IP once connected to ESP32's AP - check Serial output on Pi or router client list
const char* mqtt_user = "blueberry";
const char* mqtt_pass = "blueberry";

const char* topic_cmd = "wallbox/relay/cmd";
const char* topic_status = "wallbox/relay/status";

#define RELAY_PIN 23

WiFiClient espClient;
PubSubClient client(espClient);


void callback(char* topic, byte* payload, unsigned int length) {
  String msg;
  for (unsigned int i = 0; i < length; i++) msg += (char)payload[i];
  Serial.println("Received on " + String(topic) + ": " + msg);

  if (msg == "ON") {
  //  digitalWrite(RELAY_PIN, LOW);
    client.publish(topic_status, "relay_on");
  } else if (msg == "OFF") {
  //  digitalWrite(RELAY_PIN, HIGH);
    client.publish(topic_status, "relay_off");
  }
}

void reconnect() {
  while (!client.connected()) {
    Serial.print("Connecting to MQTT...");
    if (client.connect("ESP32Client", mqtt_user, mqtt_pass)) {
      Serial.println("connected");
      client.subscribe(topic_cmd);
    } else {
      Serial.print("failed, rc=");
      Serial.print(client.state());
      delay(2000);
    }
  }
}

void setup() {
  Serial.begin(115200);
  pinMode(RELAY_PIN, OUTPUT);
  digitalWrite(RELAY_PIN, HIGH);

  WiFi.mode(WIFI_AP);
  WiFi.softAP(ap_ssid, ap_password);
  Serial.print("AP IP address: ");
  Serial.println(WiFi.softAPIP());
  
  client.setServer(mqtt_server, 1883);
  client.setCallback(callback);
}

void loop() {
  if (!client.connected()) reconnect();
  client.loop();
}
#include <WiFi.h>
#include <PubSubClient.h>
#include <SPI.h>
#include <U8g2lib.h>
#include <ArduinoJson.h> 

// AP
const char* ap_ssid = "ESP32_IOT";
const char* ap_password = "12345678";

// MQTT
const char* mqtt_server = "192.168.4.2"; // Pi's IP once connected to ESP32's AP - check Serial output on Pi or router client list
const char* mqtt_user = "blueberry";
const char* mqtt_pass = "blueberry";

const char* topic_cmd = "wallbox/relay/cmd";
const char* topic_status = "wallbox/relay/status";
const char* topic_data = "wallbox/data";
const char* topic_connection = "wallbox/connection";

// PINS
#define RELAY_PIN 12
#define SPI_DIN 23
#define SPI_DO 19
#define SPI_CLK 18
#define SCREEN_CS 4
#define SCREEN_DC 17
#define SCREEN_RES 16
#define MEAS_CS 5

WiFiClient espClient;
PubSubClient client(espClient);

bool relay_status;

U8G2_SSD1327_WS_128X128_F_4W_HW_SPI u8g2(U8G2_R0, SCREEN_CS, SCREEN_DC, SCREEN_RES);
SPISettings measSPISettings(1000000, MSBFIRST, SPI_MODE0);

#define DATA_INTERVAL 1000
unsigned long lastDataMillis = 0;

void callback(char* topic, byte* payload, unsigned int length) {
  StaticJsonDocument<128> doc;
  DeserializationError error = deserializeJson(doc, payload, length);
  const char* cmd = doc["command"];

  if (error){
    Serial.print("JSON parse failed: ");
    Serial.println(error.c_str());
  }

  String msg;
  for (unsigned int i = 0; i < length; i++) msg += (char)payload[i];
  Serial.println("Received on " + String(topic) + ": " + msg);
  if (String(cmd) == "shutdown" || msg == "OFF") {
    //  digitalWrite(RELAY_PIN, HIGH);
    relay_status = false;
    Serial.println("Shutting Down");
  } else if (String(cmd) == "restore" || msg == "ON") {
    //  digitalWrite(RELAY_PIN, LOW);
    relay_status = true;
  }
  publishRelay();
  updateDisplay();
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

void updateDisplay() {
  u8g2.clearBuffer();
  u8g2.setFont(u8g2_font_7x14B_tr);
  u8g2.drawStr(20,20, relay_status ? "Relay: Active" : "Relay: Inactive");
  u8g2.drawStr(20,40, client.connected() ? "RPi: Connected" : "RPi: Not Connected");
  u8g2.sendBuffer();
}
float readMeasurement() {
  digitalWrite(MEAS_CS, LOW);
  SPI.beginTransaction(measSPISettings);
  uint16_t raw = SPI.transfer16(0x0000);
  SPI.endTransaction();
  digitalWrite(MEAS_CS, HIGH);
  return raw * 0.001f; //filler
}
void publishMeasurement() {
  float val = readMeasurement();
  char payload[64];
  snprintf(payload, sizeof(payload), "{\"val\":%.3f,\"ts\":%lu}", val, millis());
  client.publish(topic_data, payload);
}
void publishRelay() {
  char payload[64];
  snprintf(payload, sizeof(payload), "{\"relay_status\":%d,\"ts\":%lu}", relay_status, millis());
  client.publish(topic_status, payload);
}
void setup() {
  Serial.begin(115200);
  pinMode(RELAY_PIN, OUTPUT);
  digitalWrite(RELAY_PIN, HIGH);

  // WIFI
  WiFi.mode(WIFI_AP);
  WiFi.softAP(ap_ssid, ap_password);
  Serial.print("AP IP address: ");
  Serial.println(WiFi.softAPIP());
  // MQTT
  client.setServer(mqtt_server, 1883);
  client.setCallback(callback);
  // DISPLAY
  relay_status = true;
  u8g2.begin();
  updateDisplay();
}

void loop() {
  if (!client.connected()) reconnect();
  client.loop();
  if (millis() - lastDataMillis >= DATA_INTERVAL) {
    lastDataMillis = millis();
    publishMeasurement();
    publishRelay();
    updateDisplay();
  }
}
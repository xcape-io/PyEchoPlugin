/* ArduinoEchoProps.ino
   MIT License (c) Faure Systems <dev at faure dot systems>

   Props to echo messages to its sender.

   Requirements:
   - install ArduinoProps.zip library and dependencies (https://github.com/fauresystems/ArduinoProps)
*/
#include "ArduinoProps.h"

// Setup your WiFi network
const char* ssid = "YOUR_WIFI_SSID";
const char *passphrase = "YOUR_WIFI_PASSWORD";

// If you're running xcape.io Room software you have to respect props inbox/outbox
// topicw syntax: Room/[escape room name]/Props/[propsname]/inbox|outbox
// https://xcape.io/go/room

WifiProps props(u8"Arduino Echo", // as MQTT client id, should be unique per client for given broker
                u8"Room/My room/Props/Arduino Echo/inbox",
                u8"Room/My room/Props/Arduino Echo/outbox",
                "192.168.1.42", // your MQTT server IP address
                1883); // your MQTT server port;

PropsDataText last_echo(u8"last_echo");
PropsDataText rssi(u8"rssi");

void pollRssi(); // forward
PropsAction rssiPollingAction = PropsAction(10*1000, pollRssi);

bool wifiBegun(false);

void setup()
{
  Serial.begin(9600);

  props.addData(&last_echo);
  props.addData(&rssi);

  props.begin(InboxMessage::run);

  // At this point, the broker is not connected yet
}

void loop()
{
  if (!wifiBegun) {
    WiFi.begin(ssid, passphrase);
    Serial.println(WiFi.firmwareVersion());
    delay(250); // acceptable freeze for this props (otherwise use PropsAction for async-like behavior)
    // do static IP configuration disabling the dhcp client, must be called after every WiFi.begin()
    String fv = WiFi.firmwareVersion();
    if (fv.startsWith("1.0")) {
      Serial.println("Please upgrade the firmware for static IP");
      // see https://github.com/fauresystems/ArduinoProps/blob/master/WifiNinaFirmware.md
    }
    else {
      WiFi.config(IPAddress(192, 168, 1, 201), // local_ip
                  IPAddress(192, 168, 1, 1),  // dns_server
                  IPAddress(192, 168, 1, 1),  // gateway
                  IPAddress(255, 255, 255, 0)); // subnet
    }
    if (WiFi.status() == WL_CONNECTED) {
      wifiBegun = true;
      Serial.println(WiFi.localIP());
      Serial.println(WiFi.subnetMask());
      Serial.println(WiFi.gatewayIP());
    } else {
      WiFi.end();
    }
  } else if (wifiBegun && WiFi.status() != WL_CONNECTED) {
    WiFi.end();
    wifiBegun = false;
  }

  props.loop();

  rssiPollingAction.check();
}

void InboxMessage::run(String a) {

  if (a == u8"app:startup")
  {
    props.sendAllData();
    props.sendDone(a);
  }
  else if (a == u8"reset-mcu")
  {
    props.resetMcu();
  }
  else if (a.startsWith("echo:"))
  {
    String text = a.substring(5);
    last_echo.setValue(text);
    props.sendMesg(text);

    props.sendAllData(); // all data change, we don't have to be selctive then
    props.sendDone(a); // acknowledge props command action
  }

  else
  {
    // acknowledge omition of the props command
    props.sendOmit(a);
  }
}

void pollRssi() {
  rssi.setValue(WiFi.RSSI() + String(" dBm")); // https://www.metageek.com/training/resources/understanding-rssi.html
}

#include <OneWire.h>
#include <DallasTemperature.h>

#define ONE_WIRE_BUS 5
DeviceAddress Thermometer;
OneWire oneWire(ONE_WIRE_BUS);
DallasTemperature DS18B20(&oneWire);
String id;
uint8_t address[8];

void setup() {
  Serial.begin(115200);
  delay(10);
  DS18B20.begin();
  delay(100);
}

void loop() {
          DS18B20.getAddress(Thermometer, 0);
          id = "";
          for (uint8_t k = 0; k < 8; k++)
          {
            if (Thermometer[k] < 16) id = id + "0";
            id = id + String(Thermometer[k], HEX);
          }
          if (id.length() == 16) {
          Serial.println(id);}
          delay(100);
        }

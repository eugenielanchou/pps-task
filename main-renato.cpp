#include "HardwareSerial.h"
#include <Arduino.h>

const uint8_t MOTEUR = 3;
const unsigned long DURATION_DEFAULT_MS = 50;
const unsigned long DURATION_MAX = 3000;

bool motor_active = false;
unsigned long motor_start_time = 0;
unsigned long motorDuration = 0;
int motor_intensity = 0;

void startMotor(unsigned long duration, int intensity){
  motorDuration = duration;
  motorIntensity = intensity;

  motor_active = true;
  motor_start_time = millis();

  analogWrite(motorDuration, motorIntensity);
}

void updateMotor(){
  if (motor_active && (millis() - motor_start_time >= motorDuration)){
    analogWrite(MOTEUR, 0);
    motor_active = false;
  }
}

void setup() {
  Serial.begin(115200);
  pinMode(MOTEUR, OUTPUT);
  analogWrite(MOTEUR, 0);

  startMotor(DURATION_DEFAULT_MS, 255);
}

void clearSerial(){
  while (Serial.available()) {
    Serial.readStringUntil('\n');
  }
}

void checkDuration(unsigned long &input_duration_ms){
  if(input_duration_ms > DURATION_MAX){
    input_duration_ms = DURATION_MAX;
    Serial.print("Duration max set at DEFAULT value ");
    Serial.println(DURATION_MAX);
  }
  else if(input_duration_ms < DURATION_DEFAULT_MS){
    input_duration_ms = DURATION_DEFAULT_MS;
    Serial.print("Duration set to default value of ");
    Serial.println(DURATION_DEFAULT_MS);
  } 
  else {
    Serial.print("Duration set to input user value ");
    Serial.println(input_duration_ms);
  }
}

void checkIntensity(unsigned long &intensity){
  if(intensity > 255){
    intensity = 255;
    Serial.print("Duration max set at DEFAULT value ");
    Serial.println(intensity);
  }
  else if(intensity < 0){
    intensity = 0;
    Serial.print("Duration set to default value of ");
    Serial.println(intensity);
  } 
  else {
    Serial.print("Duration set to input user value ");
    Serial.println(input_duration_ms);
  }
}

void loop() {
  updateMotor();

  if(!Serial.available()){
    return;
  }

  if(Serial.available()>0){

    String input = Serial.readStringUntil('\n');
    input.trim();

    int virgule = input.indexOf(",");

    if (virgule > 0){
      unsigned long input_duration_ms = input.substring(0, virgule).toInt();
      int intensity = input.substring(virgula+1).toInt();
    }

    if(input_duration_ms<0){
      clearSerial();
      return;
    }

    checkDuration(input_duration_ms);
    checkIntensity(intensity);

    startMotor(input_duration_ms, intensity);

    clearSerial();
}
}


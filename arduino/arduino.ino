const uint8_t MOTEUR = 3;
const unsigned long DURATION_DEFAULT_MS = 50;
const unsigned long DURATION_MAX = 3000;

bool motor_active = false;
unsigned long motor_start_time = 0;

unsigned long motor_duration = 0;
int motor_intensity = 0;

void setMotor(unsigned long duration, int intensity){
  motor_duration = duration;
  motor_intensity = intensity;

  motor_active = true;
  motor_start_time = millis();

  analogWrite(MOTEUR, motor_intensity);
}

void updateMotor(){
  if (motor_active && (millis() - motor_start_time >= motor_duration)){
    analogWrite(MOTEUR, 0);
    motor_active = false;
  }
}

void setup() {
  Serial.begin(115200);
  pinMode(MOTEUR, OUTPUT);

  // analogWrite(MOTEUR, 150);
  // delay(2000);
  analogWrite(MOTEUR, 0);

}

void clearSerial(){
  while (Serial.available()) {
    Serial.readStringUntil('\n');
  }
}

void checkDuration(unsigned long &duration){
  if(duration > DURATION_MAX){
    duration = DURATION_MAX;
    Serial.print("Duration max set at DEFAULT value ");
    Serial.println(duration);
  }
  else if(duration < DURATION_DEFAULT_MS){
    duration = DURATION_DEFAULT_MS;
    Serial.print("DURATION set to default value of ");
    Serial.println(duration);
  } 
  else {
    Serial.print("Duration set to input user value ");
    Serial.println(duration);
  }
}

void checkIntensity(int &intensity){
  if(intensity > 255){
    intensity = 255;
    Serial.print("Intensity set to max value ");
    Serial.println(intensity);
  }
  else if(intensity < 0){
    intensity = 0;
    Serial.print("Intensity set to min value ");
    Serial.println(intensity);
  }
  else {
    Serial.print("Intensity set to input user value ");
    Serial.println(intensity);
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

    int idx_separator = input.indexOf(",");

    if (idx_separator > 0){
      motor_duration = input.substring(0, idx_separator).toInt();
      motor_intensity = input.substring(idx_separator+1).toInt();
    }

    checkDuration(motor_duration);
    checkIntensity(motor_intensity);

    setMotor(motor_duration, motor_intensity);

    clearSerial();
}
}


// four-leds v2: the same four LEDs, now with a "slow down".
//
// The laptop sends one line per detection:   E <dx> <dy>\n
// where dx, dy are the bottle's offset from the ideal spot as a percentage of
// "far" (-100..100; positive = the camera should move right / down).
// Each LED's brightness is proportional to how far you still have to go in
// its direction, so you slow down as you arrive. Inside the zone: buzzer.
//
// Pin map changed from v1, on purpose:
//   * PWM only exists on 3, 5, 6, 9, 10, 11 on an Uno. v1 had white and blue on
//     12 and 13, which can only be on or off.
//   * tone() takes Timer2, which also drives PWM on pins 3 and 11. So green
//     can't live on 11 any more, and the buzzer moves to 3, where losing PWM
//     doesn't matter.

const int RED_LEFT = 10, GREEN_RIGHT = 9, WHITE_UP = 6, BLUE_DOWN = 5;
const int BUZZER = 3, BUTTON = 2;
const int ZONE = 12;          // |dx|,|dy| <= 12 % of "far" counts as there
const unsigned long STALE_MS = 400;  // no news for this long: go dark, don't lie

unsigned long lastMsg = 0;
bool buttonWasDown = false;

void dark() {
  analogWrite(RED_LEFT, 0); analogWrite(GREEN_RIGHT, 0);
  analogWrite(WHITE_UP, 0); analogWrite(BLUE_DOWN, 0);
}

int level(int pct) {               // 0..100 % of "far" -> visible brightness
  pct = constrain(abs(pct), 0, 100);
  return pct <= ZONE ? 0 : map(pct, ZONE, 100, 20, 255);  // 20: dimmest still-visible
}

void show(int dx, int dy) {
  // dx > 0: the target sits right of where it should, so move right.
  analogWrite(GREEN_RIGHT, dx > 0 ? level(dx) : 0);
  analogWrite(RED_LEFT,    dx < 0 ? level(dx) : 0);
  analogWrite(BLUE_DOWN,   dy > 0 ? level(dy) : 0);
  analogWrite(WHITE_UP,    dy < 0 ? level(dy) : 0);
  if (abs(dx) <= ZONE && abs(dy) <= ZONE) tone(BUZZER, 1000);
  else noTone(BUZZER);
}

void setup() {
  pinMode(RED_LEFT, OUTPUT); pinMode(GREEN_RIGHT, OUTPUT);
  pinMode(WHITE_UP, OUTPUT); pinMode(BLUE_DOWN, OUTPUT);
  pinMode(BUZZER, OUTPUT);
  pinMode(BUTTON, INPUT_PULLUP);
  Serial.begin(115200);
}

void loop() {
  bool down = digitalRead(BUTTON) == LOW;
  if (down && !buttonWasDown) Serial.println("reset");
  buttonWasDown = down;

  if (Serial.available()) {
    String line = Serial.readStringUntil('\n');
    int dx, dy;
    if (sscanf(line.c_str(), "E %d %d", &dx, &dy) == 2) {
      show(dx, dy);
      lastMsg = millis();
    }
  }
  if (millis() - lastMsg > STALE_MS) { dark(); noTone(BUZZER); }
}

"""four-leds v2, laptop side: detect, compare with the ideal spot, send the error.

Differences from origin/main.py:
  * sends a signed, proportional error ("E dx dy") instead of words, so the
    Arduino can dim the LEDs as you close in (see fourleds/run.py for why);
  * fixes v1's operator-precedence bug that sent "leftdown" instead of "left,down";
  * the ideal spot is set by holding still for 3 s, as before, or by the button;
  * --dry-run prints what it would send, no Arduino needed.

    python rig/main_v2.py --port /dev/ttyUSB0
    python rig/main_v2.py --dry-run --camera 0
"""

from __future__ import annotations

import argparse
import time

import cv2
import numpy as np

FAR_FRACTION = 0.25   # an error of a quarter of the frame width is "far" (100 %)
HOLD_S = 3.0


def error_line(center, ideal, frame_w) -> str:
    far = FAR_FRACTION * frame_w
    dx = int(np.clip((center[0] - ideal[0]) / far * 100, -100, 100))
    dy = int(np.clip((center[1] - ideal[1]) / far * 100, -100, 100))
    return f"E {dx} {dy}\n"


def v1_direction(center, ideal):
    """What origin/main.py meant to send, with the parentheses it was missing."""
    direction = ""
    if abs(center[0] - ideal[0]) > 50:
        direction += "left" if center[0] < ideal[0] else "right"
    if abs(center[1] - ideal[1]) > 50:
        direction += ("" if direction == "" else ",") + ("up" if center[1] < ideal[1] else "down")
    return direction


def load_detector():
    try:
        from ultralytics import YOLO
    except ImportError:
        raise SystemExit("pip install ultralytics  (YOLOv8; class 39 is 'bottle')")
    model = YOLO("yolov8n.pt")

    def detect(frame):
        r = model(frame, classes=[39], verbose=False)[0]
        if len(r.boxes) == 0:
            return None
        x1, y1, x2, y2 = r.boxes.xyxy[0].tolist()
        return (x1 + x2) / 2, (y1 + y2) / 2

    return detect


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--port", default="/dev/ttyUSB0")
    ap.add_argument("--camera", type=int, default=0)
    ap.add_argument("--dry-run", action="store_true")
    a = ap.parse_args()

    ser = None
    if not a.dry_run:
        import serial  # pyserial

        ser = serial.Serial(a.port, 115200, timeout=0)
    send = (lambda s: print(s, end="")) if ser is None else (lambda s: ser.write(s.encode()))

    detect = load_detector()
    cap = cv2.VideoCapture(a.camera)
    ideal, still_since, last = None, None, None
    while True:
        ok, frame = cap.read()
        if not ok:
            break
        if ser is not None and ser.in_waiting and ser.readline().strip() == b"reset":
            ideal, still_since = None, None
        c = detect(frame)
        if c is None:
            still_since = None
        elif ideal is None:
            if last is not None and np.hypot(c[0] - last[0], c[1] - last[1]) < 8:
                still_since = still_since or time.time()
                if time.time() - still_since > HOLD_S:
                    ideal = c
            else:
                still_since = None
        else:
            send(error_line(c, ideal, frame.shape[1]))
        last = c
        if ideal is not None:
            cv2.circle(frame, (int(ideal[0]), int(ideal[1])), 6, (0, 255, 0), -1)
        cv2.imshow("four-leds v2", frame)
        if cv2.waitKey(1) & 0xFF == ord("q"):
            break


if __name__ == "__main__":
    main()

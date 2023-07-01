import cv2
import numpy as np
import math
import time
from directkeys import PressKey, ReleaseKey, W, A, S, D

cap = cv2.VideoCapture(0)

CHAPTER = 0

class MainPointsDetector():
    changed_time = time.time()
    minimal = None
    maxium = None
    last_distance = 0

    def define(self, current_point):
        if current_point is None:
            return False

        if self.maxium is None or current_point[1] > self.maxium[1]:
            self.maxium = current_point
        if self.minimal is None or current_point[1] < self.minimal[1]:
            self.minimal = current_point

        distance = self.maxium[1] - self.minimal[1]

        if self.last_distance is None or self.last_distance < 100:
            self.last_distance = distance
            self.changed_time = time.time()
            return False
        
        if abs(distance - self.last_distance) > 30:
            self.changed_time = time.time()
            self.last_distance = distance
            return False
        elif time.time() - self.changed_time > 0.5:
            center = ( int((self.minimal[0] + self.maxium[0])/2), int((self.minimal[1] + self.maxium[1])/2) )
            self.changed_time = time.time()
            return (True, self.minimal, self.maxium, center)


class CycleMoving():
    last_angle = None
    center = None
    changed_time = None
    up_down_state = None
    left_right_state = None
    i = 0

    def move(self, point):
        if point is None:
            return self.up_down_state

        y = int(point[1] - self.center[1])
        x = int(point[0] - self.center[0])

        angle = None
        if x != 0:
            angle = int(math.atan(y/x) * 180/math.pi) // 10
        if angle is None:
            return self.up_down_state    
        if self.last_angle is None:
            self.last_angle = angle

        if angle == self.last_angle:
            if time.time() - self.changed_time > 1:
                self.apply_up_down(3)
        else:
            self.i = self.i + (1 if angle > self.last_angle else -1)
            self.i = max(0, min(2, self.i))
    
            if self.i == 2:
                self.apply_up_down(2)
            elif self.i == 0:
                self.apply_up_down(1)
            self.last_angle = angle
            self.changed_time = time.time()
        return self.up_down_state

    def apply_up_down(self, action):
        if self.up_down_state == action:
            return
        if action == 1:
            ReleaseKey(S)
            PressKey(W)
            print("UP")
        if action == 2:
            ReleaseKey(W)
            PressKey(S)
            print("DOWN") 
        if action == 3:
            ReleaseKey(W)
            ReleaseKey(S)
            print("STOP MOVING")
        self.up_down_state = action

    def apply_left_right(self, turn):
        if self.left_right_state == turn:
            return self.left_right_state
        if turn == 1:
            ReleaseKey(D)
            PressKey(A)
            print("LEFT")
        if turn == 2:
            ReleaseKey(A)
            PressKey(D)
            print("RIGHT") 
        if turn == 3:
            ReleaseKey(A)
            ReleaseKey(D)
            print("STOP TURNING")
        self.left_right_state = turn
        return self.left_right_state


def convert_state(up_down, left_right):
    result = ""
    if up_down is None or up_down == 3:
        result += "-"
    elif up_down == 1:
        result += "W"
    elif up_down == 2:
        result += "S"
    if left_right is None or left_right == 3:
        result += "-"
    elif left_right == 1:
        result += "A"
    elif left_right == 2:
        result += "D"
    return result


MAIN_POINT_DETECTOR = MainPointsDetector()
CYCLE_MOVING = CycleMoving()

while True:
    _, frame = cap.read()
    hsv_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2HSV)

    # Green color
    green_mask = cv2.inRange(hsv_frame, np.array([40, 100, 100]), np.array([110, 255, 255])) #[ 30 100 100] [110 207 200]
    yellow_mask = cv2.inRange(hsv_frame, np.array([20, 100, 100]), np.array([30, 255, 255])) #[135  48 171] [215 128 251]
    blue_mask = cv2.inRange(hsv_frame, np.array([88, 100, 100]), np.array([168, 255, 255])) #[ 88  99 255] [168 119 255]

    contours_green, _ = cv2.findContours(green_mask, cv2.RETR_TREE, cv2.CHAIN_APPROX_SIMPLE)
    contours_yellow, _ = cv2.findContours(yellow_mask, cv2.RETR_TREE, cv2.CHAIN_APPROX_SIMPLE)
    contours_blue, _ = cv2.findContours(blue_mask, cv2.RETR_TREE, cv2.CHAIN_APPROX_SIMPLE)

    bbox_green = cv2.boundingRect(green_mask)
    bbox_blue = cv2.boundingRect(blue_mask)

    point = None

    bg = None
    bg_cnt = None
    for cnt in contours_yellow:
        contour_area = cv2.contourArea(cnt)
        if contour_area > 300 and (bg is None or bg_cnt < contour_area):
            bg = cnt
            bg_cnt = contour_area
    if bg is not None:
        x, y, w, h = cv2.boundingRect(bg)
        point = (x + int(w/2), y + int(h/2))

    blue = len([cnt for cnt in contours_blue if cv2.contourArea(cnt) > 300]) > 0
    green = len([cnt for cnt in contours_green if cv2.contourArea(cnt) > 300]) > 0

    if blue:
        turn = 1
        x, y, w, h = bbox_blue
        cv2.rectangle(frame, (x, y), (x + w, y + h), (0, 255, 0), 2)
    elif green:
        turn = 2
        x, y, w, h = bbox_green
        cv2.rectangle(frame, (x, y), (x + w, y + h), (0, 255, 0), 2)
    else:
        turn = 3

    if CHAPTER == 0:
        print("Для настройки прокрутите педали тренажера несколько раз")
        CHAPTER = 1
    elif CHAPTER == 1:
        res = MAIN_POINT_DETECTOR.define(point)
        if res:
            print("Настройка выполнена")
            CYCLE_MOVING.center = res[3]
            CYCLE_MOVING.changed_time = time.time()
            CHAPTER = 2
    elif CHAPTER == 2:
        if point is not None:
            cv2.circle(frame, point, 0, (0, 255, 0), 10)
        up_down = CYCLE_MOVING.move(point)
        left_right = CYCLE_MOVING.apply_left_right(turn)
        label = convert_state(up_down, left_right)
        cv2.putText(frame, label, (550, 450), cv2.FONT_HERSHEY_SIMPLEX, 1, (0,255,0), 3, 2)
        
    cv2.imshow("Frame", frame)
    key = cv2.waitKey(1)
    if key == 27:
        break
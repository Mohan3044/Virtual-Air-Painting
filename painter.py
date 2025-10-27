import cv2
import numpy as np
import time
import os

import track_hands as TH  # Ensure you have track_hands.py for hand tracking

# Initialize variables
brush_thickness = 10  # Default brush size
eraser_thickness = 50  # Eraser size
image_canvas = np.zeros((720, 1280, 3), np.uint8)  # Initialize the canvas

# FPS variables
currentT = 0
previousT = 0

# Load header images for toolbar
header_img = "Images"
header_img_list = os.listdir(header_img)
overlay_image = []

for i in header_img_list:
    image = cv2.imread(f'{header_img}/{i}')
    overlay_image.append(image)

cap = cv2.VideoCapture(0)
cap.set(3, 1280)
cap.set(4, 720)
cap.set(cv2.CAP_PROP_FPS, 60)

default_overlay = overlay_image[0]  # Default header image
draw_color = (255, 200, 100)  # Default drawing color

# Initialize hand detector
detector = TH.handDetector(min_detection_confidence=1)

# Initialize previous coordinates for drawing
xp, yp = 0, 0

# Brush size regions (Y-coordinates) - Adjusted positions for moving the selector down
brush_sizes = {
    "small": 10,
    "medium": 20,
    "large": 30
}
brush_y_positions = [(200, 300), (350, 450), (500, 600)]  # New Y-ranges for brush sizes (moved down)

# Initialize save functionality
saved = False

while True:
    ret, frame = cap.read()
    frame = cv2.flip(frame, 1)  # Mirror the frame for intuitive interaction
    frame[0:125, 0:1280] = default_overlay  # Add header image

    # Draw the brush size selector with circles instead of rectangles
    for i, (y1, y2) in enumerate(brush_y_positions):
        center = (1180, (y1 + y2) // 2)  # X-coordinate is fixed, Y-coordinate is the center of the circle
        radius = (y2 - y1) // 2  # Radius of the circle based on the height of the region
        cv2.circle(frame, center, radius, (255, 255, 255), -1)  # Circle background
        size_label = ["Small", "Medium", "Large"][i]
        cv2.putText(frame, size_label, (1150, y1 + 50), fontFace=cv2.FONT_HERSHEY_SIMPLEX, fontScale=0.5, color=(0, 0, 0), thickness=1)

    # Detect hands
    frame = detector.findHands(frame, draw=True)
    landmark_list = detector.findPosition(frame, draw=False)

    if len(landmark_list) != 0:
        # Index and middle finger coordinates
        x1, y1 = (landmark_list[8][1:])  # Index finger
        x2, y2 = landmark_list[12][1:]  # Middle finger    

        # Finger status
        my_fingers = detector.fingerStatus()
        if my_fingers[1] and my_fingers[2]:  # Selection mode
            xp, yp = 0, 0
            if y1 < 125:  # Check if within the toolbar region
                if 200 < x1 < 340:
                    default_overlay = overlay_image[0] 
                    draw_color = (255, 0, 0)  # Blue
                elif 340 < x1 < 500:
                    default_overlay = overlay_image[1]
                    draw_color = (47, 225, 245)  # Light Blue
                elif 500 < x1 < 640:
                    default_overlay = overlay_image[2]
                    draw_color = (197, 47, 245)  # Purple
                elif 640 < x1 < 780:
                    default_overlay = overlay_image[3]
                    draw_color = (53, 245, 47)  # Green
                elif 1100 < x1 < 1280:
                    default_overlay = overlay_image[4]
                    draw_color = (0, 0, 0)  # Eraser (Black)

            # Brush size selector (based on circle selection)
            if 1180 < x1 < 1260:
                for idx, (y_start, y_end) in enumerate(brush_y_positions):
                    if y_start < y1 < y_end:
                        brush_thickness = list(brush_sizes.values())[idx]  # Update brush size
                        eraser_thickness = brush_thickness * 5  # Adjust eraser size accordingly
                        break

            cv2.putText(frame, 'Color Selector Mode', (900, 680), fontFace=cv2.FONT_HERSHEY_COMPLEX, color=(0, 255, 255), thickness=2, fontScale=1)
            cv2.line(frame, (x1, y1), (x2, y2), color=draw_color, thickness=3)

        if my_fingers[1] and not my_fingers[2]:  # Drawing mode
            cv2.putText(frame, "Writing Mode", (900, 680), fontFace=cv2.FONT_HERSHEY_COMPLEX, color=(255, 255, 0), thickness=2, fontScale=1)
            cv2.circle(frame, (x1, y1), 15, draw_color, thickness=-1)

            if xp == 0 and yp == 0:  # Initialize previous coordinates
                xp, yp = x1, y1

            # Draw on the canvas
            if draw_color == (0, 0, 0):  # Eraser
                cv2.line(frame, (xp, yp), (x1, y1), color=draw_color, thickness=eraser_thickness)
                cv2.line(image_canvas, (xp, yp), (x1, y1), color=draw_color, thickness=eraser_thickness)
            else:  # Brush
                cv2.line(frame, (xp, yp), (x1, y1), color=draw_color, thickness=brush_thickness)
                cv2.line(image_canvas, (xp, yp), (x1, y1), color=draw_color, thickness=brush_thickness)

            xp, yp = x1, y1  # Update previous coordinates

    # Merge the canvas with the frame
    img_gray = cv2.cvtColor(image_canvas, cv2.COLOR_BGR2GRAY)
    _, imginv = cv2.threshold(img_gray, 50, 255, cv2.THRESH_BINARY_INV)
    imginv = cv2.cvtColor(imginv, cv2.COLOR_GRAY2BGR)
    frame = cv2.bitwise_and(frame, imginv)
    frame = cv2.bitwise_or(frame, image_canvas)

    # Check for both thumbs up (for saving)
    if len(landmark_list) > 0:
        fingers_status = detector.fingerStatus()
        # Check if both thumbs are up
        if fingers_status[0] == 1 and fingers_status[4] == 1:
            if not saved:
                saved = True
                # Generate filename with timestamp
                timestamp = int(time.time())
                filename = f"painting_{timestamp}.png"
                # Save the canvas to Desktop
                desktop_path = os.path.join(os.path.expanduser("~"), "Desktop")
                save_path = os.path.join(desktop_path, filename)
                cv2.imwrite(save_path, image_canvas)  # Save the canvas
                print(f"Painting saved as {save_path}")
        elif fingers_status[0] == 0 or fingers_status[4] == 0:
            saved = False  # Reset saved flag when thumbs are not up

    # Display FPS
    currentT = time.time()
    fps = 1 / (currentT - previousT)
    previousT = currentT
    cv2.putText(frame, 'Client FPS:' + str(int(fps)), (10, 670), fontFace=cv2.FONT_HERSHEY_SIMPLEX, fontScale=1, color=(255, 0, 0), thickness=2)

    # Show the canvas and paint frame
    cv2.imshow('Canvas', image_canvas)
    cv2.imshow('Paint', frame)

    # Exit condition
    if cv2.waitKey(1) & 0xFF == ord('q'):
        break

cap.release() 
cv2.destroyAllWindows()
s
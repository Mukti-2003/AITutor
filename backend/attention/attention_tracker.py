# backend/attention/attention_tracker.py

import cv2
import time

FACE_CENTER_THRESHOLD = 0.20


class AttentionTracker:

    def __init__(self):

        self.total_frames = 0
        self.attentive_frames = 0
        self.distracted_frames = 0

        self.face_detector = cv2.CascadeClassifier(
            cv2.data.haarcascades + "haarcascade_frontalface_default.xml"
        )

    def calculate_attention(self):

        cap = cv2.VideoCapture(0)

        while True:

            success, frame = cap.read()

            if not success:
                break

            frame = cv2.flip(frame, 1)

            gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)

            faces = self.face_detector.detectMultiScale(
                gray,
                scaleFactor=1.1,
                minNeighbors=5,
                minSize=(100, 100)
            )

            self.total_frames += 1

            attentive = False

            frame_h, frame_w, _ = frame.shape

            screen_center_x = frame_w // 2

            for (x, y, w, h) in faces:

                face_center_x = x + w // 2

                normalized_distance = abs(
                    face_center_x - screen_center_x
                ) / screen_center_x

                if normalized_distance < FACE_CENTER_THRESHOLD:
                    attentive = True

                color = (0, 255, 0) if attentive else (0, 0, 255)

                cv2.rectangle(
                    frame,
                    (x, y),
                    (x + w, y + h),
                    color,
                    2
                )

            if attentive:
                self.attentive_frames += 1
            else:
                self.distracted_frames += 1

            attention_score = (
                self.attentive_frames / self.total_frames
            ) * 100

            cv2.putText(
                frame,
                f"Attention: {'Focused' if attentive else 'Distracted'}",
                (20, 40),
                cv2.FONT_HERSHEY_SIMPLEX,
                1,
                (0, 255, 0) if attentive else (0, 0, 255),
                2
            )

            cv2.putText(
                frame,
                f"Score: {attention_score:.2f}%",
                (20, 80),
                cv2.FONT_HERSHEY_SIMPLEX,
                1,
                (255, 255, 0),
                2
            )

            cv2.imshow("AI Attention Mode", frame)

            key = cv2.waitKey(1)

            if key == ord("q"):
                break

        cap.release()

        cv2.destroyAllWindows()

        return {
            "total_frames": self.total_frames,
            "attentive_frames": self.attentive_frames,
            "distracted_frames": self.distracted_frames,
            "attention_score": round(attention_score, 2)
        }


if __name__ == "__main__":

    tracker = AttentionTracker()

    result = tracker.calculate_attention()

    print("\n===== ATTENTION REPORT =====")

    print(result)
from ultralytics import YOLO
import cv2

model = YOLO("yolo11n.pt")

# 로컬 영상 경로 가져오기
video_path = "videos/test.mp4"

# 로컬 영상으로 예측하기
results = model(video_path, stream=True)

# 스트리밍 결과를 반복해서 소비해야 화면이 뜸
for r in model(source=video_path, stream=True, conf=0.25, imgsz=640, show=False):
    # r.plot() -> 감지 박스가 그려진 numpy 이미지(BGR)
    im0 = r.plot()
    cv2.imshow("YOLO-LocalVideo", im0)

    # ESC 키 누르면 종료
    if cv2.waitKey(1) == 27:
        break

cv2.destroyAllWindows()

# 파일명: yolo_seg_ad_placement.py (수정 버전)

from ultralytics import YOLO
import cv2
import numpy as np

#------ 파일 경로 설정 ------#
video_path = 'videos/sag_sample_cut.mp4'
ad_image_path = 'data/images/toreta.png' # 알파 채널이 있는 PNG 이미지
output_video_path = 'videos/output_video_with_toreta_ad.mp4' # 출력 파일명 변경

#------ YOLO-Seg 모델 로드 ------#
model = YOLO('yolov8n-seg.pt') # yolov8n-seg.pt 가 정확한 모델명입니다.

#------ 영상 및 이미지 로드 ------#
vcap = cv2.VideoCapture(video_path)
if not vcap.isOpened():
    print(f"Error: Failed to open video: {video_path}")
    exit()

# ad_image는 투명도를 포함한 BGRA (4채널)로 로드됩니다.
ad_image_bgra = cv2.imread(ad_image_path, cv2.IMREAD_UNCHANGED)
if ad_image_bgra is None:
    print(f"Error: Failed to open ad image file {ad_image_path}")
    exit()

# ad_image_bgra가 4채널이 아닐 경우 (예: PNG인데 알파 채널이 없는 경우),
# 3채널 BGR 이미지로 읽고 4채널 BGRA로 강제 변환
if ad_image_bgra.shape[2] == 3:
    ad_image_bgra = cv2.cvtColor(ad_image_bgra, cv2.COLOR_BGR2BGRA)
    # 이때 알파 채널은 모두 불투명(255)으로 설정
    ad_image_bgra[:, :, 3] = 255


#------ 비디오 속성 가져오기 ------#
frame_width = int(vcap.get(cv2.CAP_PROP_FRAME_WIDTH))
frame_height = int(vcap.get(cv2.CAP_PROP_FRAME_HEIGHT))
fps = int(vcap.get(cv2.CAP_PROP_FPS))

#------ 결과 영상을 저장할 VideoWriter 객체 생성 ------#
fourcc = cv2.VideoWriter_fourcc(*'mp4v') 
out = cv2.VideoWriter(output_video_path, fourcc, fps, (frame_width, frame_height))

#------ 객체 감지 및 광고 삽입 루프 ------#
while vcap.isOpened():
    ret, frame = vcap.read()
    if not ret:
        break

    # YOLO-Seg 객체 탐지
    # 'bottle' 객체 클래스(39)를 지정합니다
    results = model(frame, conf=0.5, classes=[39])

    # 감지된 결과를 순회
    for result in results:
        masks = result.masks
        boxes = result.boxes

        if masks is not None:
            for i, mask_data in enumerate(masks.data): # masks.data는 PyTorch Tensor
                x1, y1, x2, y2 = map(int, boxes[i].xyxy[0])
                ad_area_width = x2 - x1
                ad_area_height = y2 - y1

                # 유효성 검사 (크기가 0이하가 되는 경우 방지)
                if ad_area_width <= 0 or ad_area_height <= 0:
                    continue

                # 1. YOLO segmentation mask를 타겟 객체 크기에 맞게 리사이즈 (넘파이 배열로 변환)
                # 이 마스크는 0 또는 1 값을 가집니다. (객체 안: 1, 객체 밖: 0)
                yolo_mask_resized = cv2.resize(mask_data.cpu().numpy().astype(np.uint8), 
                                               (ad_area_width, ad_area_height))

                # 2. 광고 이미지(BGRA)를 타겟 객체 크기에 맞게 리사이즈
                resized_ad_bgra = cv2.resize(ad_image_bgra, (ad_area_width, ad_area_height))

                # 3. 오버레이할 영역(ROI) 설정
                roi = frame[y1:y2, x1:x2] # BGR (3채널)

                # 4. 광고 이미지의 알파 채널과 BGR 채널 분리
                ad_bgr = resized_ad_bgra[:, :, 0:3] # 광고 이미지 BGR 부분
                ad_alpha = resized_ad_bgra[:, :, 3] / 255.0 # 광고 이미지 알파 채널 (0.0 ~ 1.0)

                # 5. YOLO 마스크와 광고 이미지의 알파 채널을 결합하여 최종 투명도 마스크 생성
                # YOLO 마스크가 1인 영역에만 광고 이미지의 알파 채널이 적용되도록 함
                final_alpha_mask = yolo_mask_resized.astype(np.float32) * ad_alpha 
                # (yolo_mask_resized는 0 또는 1, ad_alpha는 0.0 ~ 1.0)

                # 6. 알파 블렌딩 (픽셀 단위 합성)
                # (1-alpha) * 원본_픽셀 + alpha * 광고_픽셀
                for c in range(0, 3): # B, G, R 각 채널에 대해 반복
                    roi[:, :, c] = (roi[:, :, c] * (1 - final_alpha_mask) +
                                    ad_bgr[:, :, c] * final_alpha_mask).astype(np.uint8)
                
                # 합성된 ROI를 원본 프레임에 다시 삽입
                frame[y1:y2, x1:x2] = roi

    # 결과 프레임 화면에 표시 (크기 조절)
    display_frame = cv2.resize(frame, (900, 600))
    cv2.imshow("Yolo Advertisement Placement", display_frame)

    # 결과 영상을 파일로 저장
    out.write(frame)
    
    # 'Esc' 키를 누르면 종료
    if cv2.waitKey(1) & 0xFF == 27:
        break
    
# ----- 리소스 해제 ----- #
vcap.release()
out.release()
cv2.destroyAllWindows()
print(f"Video with ad has been saved to {output_video_path}")
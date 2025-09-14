from ultralytics import YOLO
import cv2

#------ 파일 경로 설정 ------#
# 영상의 경로
video_path = 'videos/sample_cut.mp4'
# 광고 이미지 경로
ad_image_path = 'data/images/samsungphone.jpg'
# 광고 영상 저장 경로
output_video_path = 'videos/output_video_with_samsung_ad.mp4'

#------ YOLO 모델 로드 ------#
model = YOLO('yolov8n.pt')

#------ 영상 및 이미지 로드 ------#

# 영상 읽기
vcap = cv2.VideoCapture(video_path)
if not vcap.isOpened():
    print(f"Error: Failed to open video: {video_path}")
    exit()

# 이미지 읽기
ad_image = cv2.imread(ad_image_path, cv2.IMREAD_UNCHANGED) #IMREAD_UNCHANGED : alpha channel투명도 정보 유지
if ad_image is None:
    print(f"Error: Failed to open ad image file {ad_image_path}")
    exit()

#------ 비디오 속성 가져오기 ------#
frame_width = int(vcap.get(cv2.CAP_PROP_FRAME_WIDTH)) # 비디오 프레임의 너비를 픽셀단위로 가져옴
frame_height = int(vcap.get(cv2.CAP_PROP_FRAME_HEIGHT)) # 비디오 프레임의 높이를 픽셀단위로 가져옴
fps = int(vcap.get(cv2.CAP_PROP_FPS)) # 비디오의 초당 프레임 수를 가져옴


#------ 결과 영상을 저장할 VideoWriter 객체 생성 (코덱 설정 필요) ------#

# 코덱(Codec) - 코덱은 coder와 decoder의 합성어로, 미디어 데이터를 압축하거나 압축을 해제하는 데 사용되는 기술(mp4v는 MPEG-4 비디오 코덱)
fourcc = cv2.VideoWriter_fourcc(*'mp4v') # fourcc 는 four character code의 약자, 특정 코덱의 종류를 나타내는 4byte 코드
out = cv2.VideoWriter(output_video_path, fourcc, fps, (frame_width, frame_height)) # VideoWriter 객체를 초기화

#------ 객체 감지 및 광고 삽입 루프 ------#

while vcap.isOpened():
    ret, frame = vcap.read()
    if not ret:
        break

    # YOLO 객체 탐지
    # 'labtop', 'tv' 등 광고를 놓고싶은 객체 클래스 지정
    results = model(frame, conf=0.5, classes=[62]) # 예시 62(TV)

    # 감지된 결과를 순회
    for result in results:
        # 감지된 객체들의 바운딩 박스 가져오기
        boxes = result.boxes
        for box in boxes:
            x1, y1, x2, y2 = map(int, box.xyxy[0])
            # 광고 이미지의 크기 조절 비율값(0~1 사이)
            scale = 0.8 

            # 바운딩 박스 크기에 맞춰 광고 이미지 크기 조절(비율 적용)
            ad_width = int((x2 - x1) * scale)
            ad_height = int((y2 - y1) * scale)

            # 광고 이미지를 비율에 맞게 리사이즈
            resized_ad = cv2.resize(ad_image, (ad_width, ad_height))

            # 광고 이미지를 바운딩 박스 안쪽 중앙 정렬되게 배치
            offset_x = x1 + (x2 - x1 - ad_width) // 2
            offset_y = y1 + (y2 - y1 - ad_height) // 2
            
            # 광고 이미지를 영상 프레임에 합성
            # 알파(투명도)채널이 없는 이미지의 경우, 아래처럼 영역 복사
            # frame[y1:y2, x1:x2] = resized_ad

            # 비율 조정된 광고 이미지를 영상 프레임에 합성
            frame[offset_y:offset_y + ad_height, offset_x:offset_x + ad_width] = resized_ad
            
    # 결과 프레임 화면에 표시
    display_frame = cv2.resize(frame, (800, 600))

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
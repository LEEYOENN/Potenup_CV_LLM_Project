from ultralytics import YOLO
import cv2
import os
import shutil
import uuid
from fastapi import FastAPI, APIRouter, UploadFile, File, HTTPException
import json
from fastapi.responses import JSONResponse

# 비디오 관련 엔드포인트를 위한 API 라우터 생성
router = APIRouter()
# 이 라우터를 메인 FastAPI 앱에 포함시키는 예시
# from .ad_attach_api import router # 'ad_attach_api' 파일에서 'router'를 가져옵니다.
# app = FastAPI()
# app.include_router(router)

#--------------------- 영상에 광고 이미지 삽입 api ---------------------------------#

# 모델 및 출력 디렉토리 전역 변수로 설정
model = YOLO("yolov8n.pt")
UPLOAD_DIR = "../../data/uploded_videos"
PROCESSED_DIR = "../../data/processed_videos"
AD_DATA_FILE = "../../data/json/ad_data.json"

# 디렉토리가 없다면 생성
os.makedirs(UPLOAD_DIR, exist_ok=True)
os.makedirs(PROCESSED_DIR, exist_ok=True)

def process_video_with_ad(video_path: str, ad_image_path: str, output_path: str, target_class: int=62):
    """
    동영상을 처리하여 특정 객체를 감지하고 광고 이미지 덮어 씌웁니다.

    Args:
        video_path: 입력 동영상 경로
        ad_image_path: 삽입할 광고 이미지 경로
        output_path: 처리된 동영상을 저장할 경로
        target_class: 광고를 삽입할 객체의 YOLO 클래스 ID

    """

    vcap = cv2.VideoCapture(video_path)
    if not vcap.isOpened():
        raise HTTPException(status_code=500, detail=f"Failed to open video file: {video_path}")
    
    ad_image = cv2.imread(ad_image_path, cv2.IMREAD_UNCHANGED)
    if ad_image is None:
        raise HTTPException(status_code=500, detail=f"Failed to open ad image file: {ad_image_path}")

    frame_width = int(vcap.get(cv2.CAP_PROP_FRAME_WIDTH))
    frame_height = int(vcap.get(cv2.CAP_PROP_FRAME_HEIGHT))
    fps = int(vcap.get(cv2.CAP_PROP_FPS))
    fourcc = cv2.VideoWriter_fourcc(*'mp4v')
    out = cv2.VideoWriter(output_path, fourcc, fps, (frame_width, frame_height))

    while vcap.isOpened():
        ret, frame = vcap.read()
        if not ret:
            break

        results = model(frame, conf=0.5, classes=[target_class])

        for result in results:
            boxes = result.boxes
            
            for box in boxes:
                x1, y1, x2, y2 = map(int, box.xyxy[0])

                scale = 0.8
                ad_width = int((x2 - x1) * scale)
                ad_height = int((y2 - y1) * scale)
                
                #cv2.resize()에 유효한 크기일때만 수행
                if ad_width > 0 and ad_height > 0:
                    resized_ad = cv2.resize(ad_image, (ad_width, ad_height))
                    offset_x = x1 + (x2 - x1 - ad_width) // 2
                    offset_y = y1 + (y2 - y1 - ad_height) // 2

                    # 광고 이미지가 프레임에서 벗어나지 않도록
                    x_start = max(0, offset_x)
                    y_start = max(0, offset_y)
                    x_end = min(frame_width, offset_x + ad_width)
                    y_end = min(frame_height, offset_y + ad_height)

                    frame[y_start:y_end, x_start:x_end] = resized_ad

        out.write(frame)
    
    vcap.release()
    out.release()
    print(f"Video with ad has been saved to {output_path}")


# 업로드 영상과 삽입할 광고이미지 받아서 광고 삽입 영상 반환
@router.post("/video/ad_attach")
async def attach_ad_to_video(
    video_file: UploadFile = File(...),
    ad_id = int
):
    """
    지정된 객체를 감지하여 광고 이미지를 동영상에 덧씌웁니다.

    Args:
        video_file (UploadFile): 처리할 동영상 파일
        ad_id (int): 삽입할 광고이미지를 찾기위한 ID

    Returns:
        처리된 동영상 파일의 경로를 담은 딕셔너리
    """
    # 1. 업로드된 동영상을 임시로 저장 upload_dir + file_path
    video_path = os.path.join(UPLOAD_DIR, video_file.filename)
    try:
        # 비디오파일은 이진 데이터임, 데이터를 byte 단위로 쓰기
        with open(video_path, "wb") as buffer:
            # 첫번째 파일 객체의 내용을 읽어 두번째 파일 객체에 쓰는 기능
            shutil.copyfileobj(video_file.file, buffer)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to save video file: {e}")
    
    # 2. 처리된 동영상의 출력 경로 정의
    unique_filename = f"{uuid.uuid4()}_{video_file.filename}"
    output_path = os.path.join(PROCESSED_DIR, unique_filename)

    # 3. json 데이터에서 광고 이미지 경로를 가져오기
    try:
        with open(AD_DATA_FILE, 'r', encoding="utf-8") as f:
            ad_data = json.load(f)
    except FileNotFoundError:
        raise HTTPException(status_code=500, detail=f"Ad data file not found at {AD_DATA_FILE}")

    # ad_id와 일치하는 데이터를 찾습니다.
    for ad in ad_data:
        ad_info = next((ad for ad in ad_data if ad["id"] == ad_id), None)

    if ad_info is None:
        raise HTTPException(status_code=404, detail=f"Ad with ID {ad_id} not found.")

    # 4. 동영상 처리
    try:
        process_video_with_ad(video_path, ad_image_path, output_path, target_class=62)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to video processing: {e}")
    finally:
        # 5. 임시동영상 파일 정리
        if os.path.exists(video_path):
            os.remove(video_path)
    
    return JSONResponse(content={"message": "Video processed successfully", "output_video_path": output_path},
                        status_code=200
                        )



    
# 광고 업체가 자신의 정보와 객체 이미지 입력 후 광고 이미지 생성

# 광고 업체가 이미지 확인하고 자신의 정보 등록

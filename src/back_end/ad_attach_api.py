from ultralytics import YOLO
import cv2
import os
import shutil
import uuid
from fastapi import FastAPI, APIRouter, UploadFile, File, HTTPException, Form
import json
from fastapi.responses import JSONResponse
from pathlib import Path
from fastapi.staticfiles import StaticFiles
import math

# 비디오 관련 엔드포인트를 위한 API 라우터 생성
attach_router = APIRouter()
# 이 라우터를 메인 FastAPI 앱에 포함시키는 예시
# from .ad_attach_api import router # 'ad_attach_api' 파일에서 'router'를 가져옵니다.
# app = FastAPI()
# app.include_router(router)

#--------------------- 영상에 광고 이미지 삽입 api ---------------------------------#

# 모델 및 출력 디렉토리 전역 변수로 설정
model = YOLO("yolov8n.pt")

BASE_DIR = Path(__file__).resolve().parent.parent.parent

UPLOAD_DIR = BASE_DIR / "data" / "uploaded_videos"
PROCESSED_DIR = BASE_DIR / "data" / "processed_videos"
AD_DATA_FILE = BASE_DIR / "data" / "json" / "ad_data.json"

# 디렉토리가 없다면 생성
os.makedirs(UPLOAD_DIR, exist_ok=True)
os.makedirs(PROCESSED_DIR, exist_ok=True)

# # 이미지를 웹에서 접근 가능하게 설정
# attach_router.mount("/processed_videos", StaticFiles(directory=PROCESSED_DIR), name="processed_videos")

# help 함수
def process_video_with_ad(video_path: str, ad_image_path: str, output_path: str, target_class: int = 62):
    """
    첫 감지 시 위치를 고정하고,
    이후 프레임에서는 '해당 프레임에서 물체가 감지되었을 때만' 고정 위치에 광고를 보여줍니다.
    감지되지 않으면 원본 프레임을 그대로 사용합니다.
    """
    vcap = cv2.VideoCapture(video_path)
    if not vcap.isOpened():
        raise HTTPException(status_code=500, detail=f"Failed to open video file: {video_path}")

    ad_image = cv2.imread(ad_image_path, cv2.IMREAD_UNCHANGED)  # alpha 포함 가능
    if ad_image is None:
        raise HTTPException(status_code=500, detail=f"Failed to open ad image file: {ad_image_path}")

    frame_width = int(vcap.get(cv2.CAP_PROP_FRAME_WIDTH))
    frame_height = int(vcap.get(cv2.CAP_PROP_FRAME_HEIGHT))
    fps = int(vcap.get(cv2.CAP_PROP_FPS)) or 30
    fourcc = cv2.VideoWriter_fourcc(*'mp4v')
    out = cv2.VideoWriter(output_path, fourcc, fps, (frame_width, frame_height))

    # --- 초기 프레임에서 첫 감지 좌표를 얻기 위한 준비 ---
    x1_fixed = y1_fixed = x2_fixed = y2_fixed = None
    first_frame_read = False

    # 알파 채널이 있는 광고 이미지를 프레임에 덮을 때 쓰는 헬퍼 (블렌딩)
    def overlay_image_alpha(bg, fg, x, y):
        """
        bg: background BGR 이미지 (수정됨)
        fg: foreground BGRA 또는 BGR 이미지
        (x,y): fg가 놓일 좌상단 좌표 (정수)
        """
        fh, fw = fg.shape[:2]
        if x >= bg.shape[1] or y >= bg.shape[0]:
            return bg  # 화면 밖이면 변경 없음

        # 계산되는 영역
        x1 = max(x, 0)
        y1 = max(y, 0)
        x2 = min(x + fw, bg.shape[1])
        y2 = min(y + fh, bg.shape[0])

        fg_x1 = x1 - x
        fg_y1 = y1 - y
        fg_x2 = fg_x1 + (x2 - x1)
        fg_y2 = fg_y1 + (y2 - y1)

        bg_region = bg[y1:y2, x1:x2]
        fg_region = fg[fg_y1:fg_y2, fg_x1:fg_x2]

        if fg_region.shape[2] == 4:
            # alpha blending
            alpha = fg_region[:, :, 3] / 255.0
            alpha = alpha[:, :, None]
            fg_rgb = fg_region[:, :, :3].astype(float)
            bg_rgb = bg_region.astype(float)
            blended = (alpha * fg_rgb + (1 - alpha) * bg_rgb).astype('uint8')
            bg[y1:y2, x1:x2] = blended
        else:
            # alpha 없으면 단순 복사
            bg[y1:y2, x1:x2] = fg_region

        return bg

    # 비디오 처리 루프: 프레임마다 감지 여부 확인
    while vcap.isOpened():
        ret, frame = vcap.read()
        if not ret:
            break

        # 모델은 BGR을 기대할 수도 있고, 사용하던 방식에 맞춰 그대로 전달
        # (필요하면 cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)로 변경)
        results = model(frame, conf=0.5, classes=[target_class])

        detected_in_frame = False
        if results and results[0].boxes:
            # 현재 프레임에서 해당 클래스가 감지됨
            detected_in_frame = True
            # 최초 고정 좌표가 없는 경우에만 고정 좌표로 저장
            if x1_fixed is None:
                first_box = results[0].boxes[0]
                x1_fixed, y1_fixed, x2_fixed, y2_fixed = map(int, first_box.xyxy[0])

        # 광고 표시 조건: 최초 고정 좌표가 존재하고, 현재 프레임에서 감지되었을 때만 표시
        if x1_fixed is not None and detected_in_frame:
            scale = 0.8
            ad_width = int((x2_fixed - x1_fixed) * scale)
            ad_height = int((y2_fixed - y1_fixed) * scale)

            if ad_width > 0 and ad_height > 0:
                resized_ad = cv2.resize(ad_image, (ad_width, ad_height), interpolation=cv2.INTER_AREA)
                offset_x = x1_fixed + (x2_fixed - x1_fixed - ad_width) // 2
                offset_y = y1_fixed + (y2_fixed - y1_fixed - ad_height) // 2

                # overlay with alpha support
                frame = overlay_image_alpha(frame, resized_ad, offset_x, offset_y)
        # else: 감지 안되면 원본 유지 (덮어쓰지 않음)

        out.write(frame)

    vcap.release()
    out.release()
    print(f"Video with ad has been saved to {output_path}")


# api


# 업로드 영상과 삽입할 광고이미지 id 받아서 광고 삽입 영상 반환
@attach_router.post("/ad_attach")
async def attach_ad_to_video(
    video_file: UploadFile = File(...),
    ad_id: int = Form(...)
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
    ad_info = next((ad for ad in ad_data if ad["id"] == ad_id), None)

    if ad_info is None:
        raise HTTPException(status_code=404, detail=f"Ad with ID {ad_id} not found.")

    # 4. 동영상 처리
    try:
        process_video_with_ad(video_path, ad_info["image_path"], output_path, target_class=62)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to video processing: {e}")
    finally:
        # 5. 임시동영상 파일 정리
        if os.path.exists(video_path):
            os.remove(video_path)
    
    # return JSONResponse(content={"message": "Video processed successfully", "output_video_path": Path(output_path).as_posix()},
    #                     status_code=200
    #                     )

     # --- 추가: 파일 존재 여부 확인 및 public_url 생성 ---
    output_path_obj = Path(output_path).resolve()
    # 로그: 파일이 실제로 존재하는지 확인 (uvicorn 콘솔에 찍힘)
    print("DEBUG: processed file exists:", output_path_obj.exists(), "->", output_path_obj)

    # public url은 fastapi에서 mount한 경로와 일치하도록 파일명만 사용
    public_url = f"/processed_videos/{output_path_obj.name}"

    return JSONResponse(
        content={
            "message": "Video processed successfully",
            "output_video_path": output_path_obj.as_posix(),   # 절대경로
            "public_url": public_url                           # 클라이언트가 바로 사용할 값
        },
        status_code=200
    )





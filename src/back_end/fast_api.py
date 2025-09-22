from fastapi import FastAPI, UploadFile, File, Form
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles
from pathlib import Path
from typing import List
import shutil
import uuid
import time

import src.stt.video_to_text as text_maker
import src.stt.text_to_video as video_maker
from src.back_end.ad_attach_api import attach_router
from src.back_end.ad_register_api import register_router

# VIDEO_PATH = Path('../../data/video/input')
BASE_DIR = Path(__file__).resolve().parent.parent.parent
VIDEO_PATH = BASE_DIR / "data" / "video" / "input"
GENERATED_AD_IMAGE_DIR = BASE_DIR / "data" / "ad_images"
PROCESSED_DIR = BASE_DIR / "data" / "processed_videos"

app = FastAPI()

# 웹에서 접근할 prefix를 /ad/images 로 하려면 이렇게 mount
app.mount("/ad/images", StaticFiles(directory=GENERATED_AD_IMAGE_DIR), name="ad_images")

# 영상을 웹에서 접근 가능하게 설정
app.mount("/processed_videos", StaticFiles(directory=PROCESSED_DIR), name="processed_videos")

app.include_router(attach_router, prefix="/video")
app.include_router(register_router, prefix="/ad")


@app.post("/video/stt")
async def send_stt_video(
    show_time: int = Form(...),           # 프론트에서 보낸 숫자 값
    video: UploadFile = File(...)       # 업로드된 영상 파일
):
    
    print('1. 영상 파일 업로드')
    # 새 이름 생성
    id = str(uuid.uuid4())
    ext = Path(video.filename).suffix
    new_filename = f"{id}{ext}"
    new_path = VIDEO_PATH / new_filename

    print('2. 영상 파일 저장')
    with open(new_path, "wb") as buffer:
        shutil.copyfileobj(video.file, buffer)  # 저장 완료될 때까지 블록
    
    print('3. csv')
    text_maker.srt_extract(id)
    
    print('4. match')
    df = video_maker.make_matched_keyword_srt_df(id)
    
    print('5. video')
    video_maker.attach_goods_image_to_video(df, id, show_time)

    return JSONResponse(content={"success": True, "id": id})

@app.post("/video/detect")
def send_detect_video():
    
    return 'detect'


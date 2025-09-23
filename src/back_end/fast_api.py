from fastapi import FastAPI, UploadFile, File, Form
from fastapi.responses import JSONResponse

from pathlib import Path
from typing import List
import shutil
import uuid

import src.stt.image_to_goods as goods_maker
import src.stt.video_to_text as text_maker
import src.stt.text_to_video as video_maker

BASE_DIR = Path(__file__).resolve().parent.parent.parent
VIDEO_PATH = BASE_DIR / "data" / "video" / "input"

app = FastAPI()

@app.post("/video/stt")
async def send_stt_video(
    video: UploadFile = File(...), # 변환할 영상 
    show_time: int = Form(...),   # 광고 노출 시간
    image: UploadFile = File(...), # 상품 이미지
    goods_link: str = Form(...),  # 상품 링크
    goods_keyword: str = Form(...)  # 상품 키워드
):

    id = str(uuid.uuid4())

    print('0. 상품 이미지 및 링크(QR화) 하나의 광고 포스터로 변환하여, 키워드와 함께 DB(JSON)에 저장')
    if image is not None:
        goods_maker.image_to_goods(id, image, goods_link, goods_keyword)
    
    print('1. 영상 파일 저장')
    ext = Path(video.filename).suffix
    new_filename = f"{id}{ext}"
    new_path = VIDEO_PATH / new_filename

    with open(new_path, "wb") as buffer:
        shutil.copyfileobj(video.file, buffer)
    
    print('2. 영상에서 자막 csv 추출')
    text_maker.srt_extract(id)
    
    print('3. 추출된 csv와 매칭되는 상품정보 가져오기')
    df = text_maker.make_matched_keyword_srt_df(id)
    
    print('4. 가져온 상품정보 새로운 영상에 추가')
    video_maker.attach_goods_image_to_video(df, id, show_time)

    return JSONResponse(content={"success": True, "id": id})

@app.post("/video/detect")
def send_detect_video():
    
    return 'detect'

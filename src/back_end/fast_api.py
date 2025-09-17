from fastapi import FastAPI, UploadFile, File, Form
from fastapi.responses import JSONResponse

from pathlib import Path
from typing import List
import shutil
import uuid
import time

import src.stt.video_to_text as text_maker
import src.stt.text_to_video as video_maker


# VIDEO_PATH = Path('../../data/video/input')
BASE_DIR = Path(__file__).resolve().parent.parent.parent
VIDEO_PATH = BASE_DIR / "data" / "video" / "input"

app = FastAPI()

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


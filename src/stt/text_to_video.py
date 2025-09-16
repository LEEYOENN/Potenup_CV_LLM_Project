import re
import pandas as pd
from konlpy.tag import Okt
import json
from pathlib import Path
from moviepy import VideoFileClip, CompositeVideoClip
from moviepy.video.VideoClip import ImageClip
import numpy as np
from PIL import Image

BASE_DIR = Path(__file__).resolve().parent.parent.parent
VIDEO_INPUT_PATH = BASE_DIR / "data" / "video" / "input"
VIDEO_OUTPUT_PATH = BASE_DIR / "data" / "video" / "output"
CSV_PATH = BASE_DIR / "data" / "csv"
JSON_PATH = BASE_DIR / "data" / "json"

def make_matched_keyword_srt_df(id: str):
    
    # 검색 키워드들(== 등록된 상품명들)
    # TODO 추후 redis로 옮기는 것 고려
    registered_goods = [
        '가죽 자켓', '청자켓', '후드', '맥코트', '신발', '바지', '선글라스', '(메시)니트', '반팔티', '이너', '아우터', 
        '데님 자켓', '데님 팬츠', '데님 트러커', '자켓', '워크자켓', '아디다스 저지', '아디다스 트랙탑', '스카프', '토니웩', '모모타로진'
    ]
    
    # Okt 객체 생성
    okt = Okt()
    df = pd.read_csv(str(CSV_PATH / f'{id}.csv'), header=None, names=["id", "start", "end", "text"])
    
    # TODO 중복으로 등장하는 키워드가 있는 경우 처음 시간대만 체크하는 것 고려
    # TODO 해당 코드 이해
    normalized_patterns = [
        re.escape(item).replace(r"\ ", r"\s*") for item in registered_goods # 공백이 있든 없든 탐지(가죽 자켓 / 가죽자켓)
    ]

    pattern = re.compile("|".join(normalized_patterns))

    # 매칭된 키워드 리스트를 새로운 컬럼으로 추가
    df["matched_keywords"] = (
        df["text"]
        .str.findall(pattern)
        .map(set)   # set으로 변환 → 중복 제거
        .map(list)  
    )

    matched_df = df[df["matched_keywords"].str.len() > 0]
    
    return matched_df
    
def time_to_seconds(time_str: str) -> int:
    
    h, m, s = map(int, time_str.split(":"))
    
    return h * 3600 + m * 60 + s
    
def attach_goods_image_to_video(matched_df, video_id: str, show_time: int):
    
    with open(str(JSON_PATH / 'fashion.json'), 'r', encoding='utf-8') as f:
        keyword_map = json.load(f)
    
    for _, row in matched_df.iterrows():
        for keyword in row['matched_keywords']:
            if keyword in keyword_map.keys():
                goods_info = keyword_map[keyword]

                video = VideoFileClip(str(VIDEO_INPUT_PATH / f'{video_id}.mp4'))

                seconds = time_to_seconds(row['start'])

                # TODO 상품 이미지가 나오는 공간을 YOLO나 SAM으로 파악하여 빈공간에 나올 수 있도록 수정(.with_position((0.7, 0.05) 값 자동화)
                img = (
                    ImageClip(str(BASE_DIR / goods_info['image_path']), duration=show_time) 
                        .with_start(seconds)
                        .with_position((0.7, 0.05), relative=True)
                )

                # 영상 + 이미지 합성
                final = CompositeVideoClip([video, img])

                # 영상 저장
                final.write_videofile(str(VIDEO_OUTPUT_PATH / f'{video_id}.mp4'), codec="libx264", audio_codec="aac")
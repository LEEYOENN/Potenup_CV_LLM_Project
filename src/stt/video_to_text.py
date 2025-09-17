from faster_whisper import WhisperModel
from pathlib import Path

import re
import uuid
import pandas as pd

BASE_DIR = Path(__file__).resolve().parent.parent.parent
VIDEO_INPUT_PATH = BASE_DIR / "data" / "video" / "input"
VIDEO_OUTPUT_PATH = BASE_DIR / "data" / "video" / "output"
CSV_PATH = BASE_DIR / "data" / "csv"
JSON_PATH = BASE_DIR / "data" / "json"

def srt_timestamp(t: float) -> str:

    ms = int(t * 1000)
    hh, ms = divmod(ms, 3600000)
    mm, ms = divmod(ms, 60000)
    ss, ms = divmod(ms, 1000)

    return f"{hh:02d}:{mm:02d}:{ss:02d}"

def srt_extract(id: str):
    
    model = WhisperModel('small', device='cpu', compute_type='int8')
    segments, info = model.transcribe(str(VIDEO_INPUT_PATH / f'{id}.mp4'), language='ko', vad_filter=False)
    
    txt_path = CSV_PATH / f'{id}.csv'

    with open(txt_path, "w", encoding="utf-8") as full_text:
        for segment in segments:   
            id = uuid.uuid4()
            line = segment.text.strip()
            full_text.write(f"{id}, {srt_timestamp(segment.start)}, {srt_timestamp(segment.end)}, {line}\n")
            
    return id

def make_matched_keyword_srt_df(id: str):
    
    # 검색 키워드들(== 등록된 상품명들)
    # TODO 추후 redis로 옮기는 것 고려
    registered_goods = [
        '가죽 자켓', '청자켓', '후드', '맥코트', '신발', '바지', '선글라스', '(메시)니트', '반팔티', '이너', '아우터', 
        '데님 자켓', '데님 팬츠', '데님 트러커', '자켓', '워크자켓', '아디다스 저지', '아디다스 트랙탑', '스카프', '토니웩', '모모타로진'
    ]
    
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
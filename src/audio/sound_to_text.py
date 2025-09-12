from faster_whisper import WhisperModel
from pathlib import Path
import uuid

CSV_PATH = Path('../../data/csv')
VIDEO_PATH = Path('../../data/video')

def srt_timestamp(t: float) -> str:

    ms = int(t * 1000)
    hh, ms = divmod(ms, 3600000)
    mm, ms = divmod(ms, 60000)
    ss, ms = divmod(ms, 1000)

    return f"{hh:02d}:{mm:02d}:{ss:02d}"

def srt_extract(video_source):
    
    model = WhisperModel('small', device='cpu', compute_type='int8')
    segments, info = model.transcribe(str(VIDEO_PATH / video_source), language='ko', vad_filter=False)

    CSV_PATH.mkdir(exist_ok=True)

    file_name = str(uuid.uuid4())
    txt_path = CSV_PATH / f'{file_name}.txt'

    with open(txt_path, "w", encoding="utf-8") as full_text:
        for segment in segments:   
            id = uuid.uuid4()
            line = segment.text.strip()
            full_text.write(f"{id}, {srt_timestamp(segment.start)}, {srt_timestamp(segment.end)}, {line}\n")
            
srt_extract('yt.mp4')
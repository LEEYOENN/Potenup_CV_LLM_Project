import json
from pathlib import Path
from moviepy import VideoFileClip, CompositeVideoClip
from moviepy.video.VideoClip import ImageClip

BASE_DIR = Path(__file__).resolve().parent.parent.parent
VIDEO_INPUT_PATH = BASE_DIR / "data" / "video" / "input"
VIDEO_OUTPUT_PATH = BASE_DIR / "data" / "video" / "output"
CSV_PATH = BASE_DIR / "data" / "csv"
JSON_PATH = BASE_DIR / "data" / "json"

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
                
def find_appropriate_goods_position(video_id: str):
    
    video = VideoFileClip(str(VIDEO_INPUT_PATH / f'{video_id}.mp4'))
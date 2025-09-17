import json
from pathlib import Path

from ultralytics import YOLO
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
                position = find_appropriate_goods_position(video_id, seconds)
                print('position', position)
                
                img = (
                    ImageClip(str(BASE_DIR / goods_info['image_path']), duration=show_time) 
                        .with_start(seconds)
                        .with_position(position, relative=True)
                )

                # 영상 + 이미지 합성
                final = CompositeVideoClip([video, img])

                # 영상 저장
                final.write_videofile(str(VIDEO_OUTPUT_PATH / f'{video_id}.mp4'), codec="libx264", audio_codec="aac")
                
def find_appropriate_goods_position(video_id: str, seconds: int):
    
    model = YOLO("yolov8n.pt")
    
    video = VideoFileClip(str(VIDEO_INPUT_PATH / f'{video_id}.mp4'))
    
    frame_w, frame_h = video.size
    frame = video.get_frame(seconds)
    
    results = model(frame)
    boxes = results[0].boxes
    
    for x1, y1, x2, y2, conf, cls in boxes.data:
        
        if cls == 0:  # 0 = person
            print("person detected:", x1, y1, x2, y2, conf)

            person_center = (x1 + x2) / 2
            video_center = frame_w / 2

            # 영상 전체 가로의 중심을 기준으로 사람의 위치를 파악
            if person_center > video_center:
                print('person is right')
                return (0.05, 0.05)  # 사람이 오른쪽 → 이미지 왼쪽
            else:
                print('person is left')
                return (0.7, 0.05)  # 사람이 왼쪽 → 이미지 오른쪽(기본값)
        
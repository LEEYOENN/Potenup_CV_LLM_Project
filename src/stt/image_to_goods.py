import json
import numpy as np
from pathlib import Path
from PIL import ImageFont, ImageDraw, Image

import shutil
import qrcode
import cv2

BASE_DIR = Path(__file__).resolve().parent.parent.parent

VIDEO_INPUT_PATH = BASE_DIR / "data" / "video" / "input"
VIDEO_OUTPUT_PATH = BASE_DIR / "data" / "video" / "output"

TOTAL_IMAGE_PATH = BASE_DIR / "data" / "image" / "total"
GOODS_IMAGE_PATH = BASE_DIR / "data" / "image" / "goods"
QR__IMAGE_PATH = BASE_DIR / "data" / "image" / "qr"

CSV_PATH = BASE_DIR / "data" / "csv"
JSON_PATH = BASE_DIR / "data" / "json" / "fashion.json"

# 한글 텍스트 출력 (윤곽선/그림자 지원)
def draw_text_korean(img, text, pos, 
                    font_path="C:/Windows/Fonts/malgunbd.ttf",
                    font_size=25, 
                    color=(0, 0, 0)):
    
    img_pil = Image.fromarray(cv2.cvtColor(img, cv2.COLOR_BGR2RGB))
    draw = ImageDraw.Draw(img_pil)
    font = ImageFont.truetype(font_path, font_size)

    # 텍스트 그림자 (회색)
    shadow_offset = 2
    draw.text((pos[0] + shadow_offset, pos[1] + shadow_offset),
            text, font=font, fill=(180, 180, 180))
    
    # 본문 텍스트
    draw.text(pos, text, font=font, fill=color)

    return cv2.cvtColor(np.array(img_pil), cv2.COLOR_RGB2BGR)


# 포스터 전체 모서리 둥글게
def round_corners(img, radius=50):

    h, w = img.shape[:2]
    rounded = np.zeros((h, w, 4), dtype=np.uint8)
    rounded[:, :, :3] = img

    mask = np.zeros((h, w), dtype=np.uint8)
    
    cv2.rectangle(mask, (radius, 0), (w - radius, h), 255, -1)
    cv2.rectangle(mask, (0, radius), (w, h - radius), 255, -1)
    cv2.circle(mask, (radius, radius), radius, 255, -1)
    cv2.circle(mask, (w - radius, radius), radius, 255, -1)
    cv2.circle(mask, (radius, h - radius), radius, 255, -1)
    cv2.circle(mask, (w - radius, h - radius), radius, 255, -1)

    rounded[:, :, 3] = mask
    
    return rounded

# 포스터 생성
def images_to_poster(id, goods_keyword):
    
    product_img = cv2.imread(str(GOODS_IMAGE_PATH / f"{id}.jpg"))
    qr_img = cv2.imread(str(QR__IMAGE_PATH / f"{id}.jpg"))

    # QR 크기 상품 폭의 80%
    qr_height = int(product_img.shape[1] * 0.8)
    qr_img_resized = cv2.resize(qr_img, (product_img.shape[1], qr_height))

    # 캔버스 생성 (흰색 → 카드 스타일)
    canvas_h = product_img.shape[0] + qr_img_resized.shape[0] + 250
    canvas_w = max(product_img.shape[1], qr_img_resized.shape[1]) + 150
    poster = np.ones((canvas_h, canvas_w, 3), dtype=np.uint8) * 255

    # 카드 영역 배경
    cv2.rectangle(poster, (20, 20), (canvas_w - 20, canvas_h - 20), (245, 245, 245), -1)

    # 상품 이미지 배치 + 그림자
    x_offset = (canvas_w - product_img.shape[1]) // 2
    shadow = poster.copy()
    cv2.rectangle(shadow,
                (x_offset + 8, 58),
                (x_offset + product_img.shape[1] + 8, 58 + product_img.shape[0] + 8),
                (200, 200, 200), -1)
    poster = cv2.addWeighted(shadow, 0.3, poster, 0.7, 0)
    poster[50:50 + product_img.shape[0], x_offset:x_offset + product_img.shape[1]] = product_img

    # QR 코드 배치 + 테두리
    y_offset = 120 + product_img.shape[0]
    x_offset = (canvas_w - qr_img_resized.shape[1]) // 2
    poster[y_offset:y_offset + qr_img_resized.shape[0], x_offset:x_offset + qr_img_resized.shape[1]] = qr_img_resized
    
    cv2.rectangle(poster,
                (x_offset - 5, y_offset - 5),
                (x_offset + qr_img_resized.shape[1] + 5, y_offset + qr_img_resized.shape[0] + 5),
                (200, 200, 200), 2)

    # 텍스트 추가
    poster = draw_text_korean(poster, goods_keyword, (90, 60))

    # 둥근 모서리 적용
    rounded_poster = round_corners(poster, radius=50)
    
    # 전체 크기를 75%로 축소
    h, w = rounded_poster.shape[:2]
    new_size = (int(w * 0.75), int(h * 0.75))
    resized_poster = cv2.resize(rounded_poster, new_size, interpolation=cv2.INTER_AREA)

    total_image_path = str(TOTAL_IMAGE_PATH / f'{id}.png')
    cv2.imwrite(total_image_path, resized_poster)

    return total_image_path


# 상품 + QR → 포스터 + JSON 저장
def image_to_goods(id, image, goods_link, goods_keyword):
    
    with open(GOODS_IMAGE_PATH / f"{id}.jpg", "wb") as buffer:
        shutil.copyfileobj(image.file, buffer)

    goods_qr = qrcode.make(goods_link)
    goods_qr.save(str(QR__IMAGE_PATH / f'{id}.jpg'))

    total_image_path = images_to_poster(id, goods_keyword)

    with open(JSON_PATH, "r", encoding="utf-8") as f:
        goods_json = json.load(f)

    goods_json[goods_keyword] = {
        "id": id,
        "image_path": total_image_path,
        "link": goods_link
    }

    with open(JSON_PATH, "w", encoding="utf-8") as f:
        json.dump(goods_json, f, ensure_ascii=False, indent=4)
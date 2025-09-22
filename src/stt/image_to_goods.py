import json
import numpy as np
from pathlib import Path

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

def image_to_goods(id, image, goods_link, goods_keyword):
    
    # 상품 이미지 저장
    with open(GOODS_IMAGE_PATH / f"{id}.jpg", "wb") as buffer:
        shutil.copyfileobj(image.file, buffer)
        
    # QR 이미지 저장
    goods_qr = qrcode.make(goods_link)
    goods_qr.save(str(QR__IMAGE_PATH / f'{id}.jpg'))
    
    # 상품 + QR 이미지 저장
    product_img = cv2.imread(str(GOODS_IMAGE_PATH / f"{id}.jpg"))
    qr_img = cv2.imread(str(QR__IMAGE_PATH / f"{id}.jpg"))
    
    qr_height = int(product_img.shape[1] * 0.8)   # QR 크기 비율 (상품 폭의 80%)
    qr_img_resized = cv2.resize(qr_img, (product_img.shape[1], qr_height))

    total_image_path = str(TOTAL_IMAGE_PATH / f'{id}.jpg')
    merged_img = np.vstack((product_img, qr_img_resized))
    cv2.imwrite(total_image_path, merged_img)

    # 기존 JSON 불러오기
    with open(JSON_PATH, "r", encoding="utf-8") as f:
        goods_json = json.load(f)

    # 새 데이터 추가
    goods_json[goods_keyword] = {"id": id, "image_path": total_image_path, "link": goods_link}

    # 다시 저장
    with open(JSON_PATH, "w", encoding="utf-8") as f:
        json.dump(goods_json, f, ensure_ascii=False, indent=4)
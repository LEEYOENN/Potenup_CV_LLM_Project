import os
import shutil
from fastapi import FastAPI, APIRouter, UploadFile, File, HTTPException, Form
import json
from fastapi.responses import JSONResponse
from pathlib import Path
from google import genai
from google.genai import types
from PIL import Image
from io import BytesIO
import uuid
from dotenv import load_dotenv
import cv2
import numpy as np

load_dotenv()

register_router = APIRouter()

BASE_DIR = Path(__file__).resolve().parent.parent.parent

GENERATED_AD_IMAGE_DIR = BASE_DIR / "data" / "ad_images"
ORIGIN_AD_IMAGE_DIR = BASE_DIR / "data" / "origin_ad_images"
AD_DATA_FILE = BASE_DIR / "data" / "json" / "ad_data.json"
LOGO_DIR = BASE_DIR / "data" / "logos"

os.makedirs(GENERATED_AD_IMAGE_DIR, exist_ok=True)
os.makedirs(ORIGIN_AD_IMAGE_DIR, exist_ok=True)

def generate_ad_image(category: str, origin_ad_image_path: str):
    """
    이미지 생성 모델 api를 사용하여 광고 이미지를 생성합니다.

    Args:
        category: 생성하는 광고 객체의 카테고리(prompt에 사용)
        origin_ad_image_path: 광고 객체의 오리지널 이미지 파일 경로
    
    Returns:
        response: 광고 이미지 생성 결과

    """

    client = genai.Client(api_key=os.getenv("GOOGLE_AI_API_KEY"))
    prompt = (
        f"After picking this {category} object, "
        "make it a good commercial image.",
    )

    image = Image.open(origin_ad_image_path)
    try:
        response = client.models.generate_content(
            model="gemini-2.5-flash-image-preview",
            contents=[prompt, image],
        )
    except Exception as e:
        print(f"Error during image generation:{e}")
        return None
    
    return response

def insert_logo_to_image(ad_image_path: str, logo_image_path: str):
    # --------- 광고이미지와 로고이미지 가져오기 --------------#
    generated_ad_image = cv2.imread(ad_image_path)
    if generated_ad_image is None:
        raise FileNotFoundError(f"Failed to open image file: {ad_image_path}")
    #generated_ad_image = cv2.cvtColor(generated_ad_image, cv2.COLOR_BGR2RGB)

    logo_image_loaded = cv2.imread(logo_image_path, cv2.IMREAD_UNCHANGED)
    if logo_image_loaded is None:
        raise FileNotFoundError(f"Failed to open logo image file: {logo_image_path}")

    #------ 로고 크기 및 위치 설정 ------#
    logo_width = 230
    aspect_ratio = logo_image_loaded.shape[1] / logo_image_loaded.shape[0] # 가로/세로 비율
    logo_height = int(logo_width / aspect_ratio)

    # 로고 리사이즈
    resized_logo = cv2.resize(logo_image_loaded, (logo_width, logo_height), interpolation=cv2.INTER_AREA)

    # 로고를 삽입할 광고 이미지의 오른쪽 하단 위치 설정
    y_offset, x_offset = 10, 10 # 하단 오른쪽 마진

    # 광고 이미지와 로고 이미지의 크기 가져오기
    ad_height, ad_width, _ = generated_ad_image.shape
    logo_height, logo_width = resized_logo.shape[0], resized_logo.shape[1]

    # ------ 로고 삽입 좌표 계산 (오른쪽 하단 기준) ------ #
    y1 = ad_height - logo_height - y_offset
    x1 = ad_width - logo_width - x_offset
    y2 = ad_height - y_offset
    x2 = ad_width - x_offset

    # 영역이 광고 이미지 범위를 벗어나지 않도록 조종
    if y2 > ad_height : y2 = ad_height
    if x2 > ad_width : x2 = ad_width

    #-------------- 알파블랜딩 수행 ---------------#
    # 로고의 BGR과 알파 채널을 분리
    if resized_logo.shape[2] == 4:
        b, g, r, alpha = cv2.split(resized_logo)
        # 알파채널을 0.0 ~ 1.0 범위로 정규화
        overlay_rgb = cv2.merge((r, g, b)) # 로고의 채널 순서를 RGB로 변경
        alpha_normalized = alpha / 255.0

    else:
        # 알파 채널이 없는 경우 (투명도가 없는 경우)
        overlay_rgb = resized_logo
        alpha_normalized = np.ones(overlay_rgb.shape[:2], dtype=overlay_rgb.dtype)

    # 광고 이미지에서 로고를 덮어쓸 영역 (ROI)
    roi = generated_ad_image[y1:y2, x1:x2]

    # roi와 overlay_rgb의 크기를 맞춰줌 (만약 경계조정으로 크기가 달라졌다면)
    overlay_rgb_cropped = overlay_rgb[:roi.shape[0], :roi.shape[1]]
    alpha_normalized_cropped = alpha_normalized[:roi.shape[0], :roi.shape[1]]

    # 알파 블렌딩 수식을 적용: 새로운 픽셀 = (원래 픽셀 * (1 - 알파)) + (오버레이 픽셀 * 알파) 
    for c in range(0, 3):
        roi[:, :, c] = (roi[:, :, c] * (1 - alpha_normalized_cropped) + overlay_rgb_cropped[:, :, c] * alpha_normalized_cropped)

    return generated_ad_image
    



# 광고 업체가 자신의 정보와 객체 이미지 입력 후 광고 이미지 생성
@register_router.post("/ad/generate_ad_image")
async def generate_ad_image_api(origin_image: UploadFile = File(...), category: str = "product"):
    """
    지정된 객체를 감지하여 광고 이미지를 동영상에 덧씌웁니다.

    Args:
        video_file (UploadFile): 처리할 동영상 파일
        ad_id (int): 삽입할 광고이미지를 찾기위한 ID

    Returns:
        처리된 동영상 파일의 경로를 담은 딕셔너리
    """
    # 1. 업로드된 오리지널 이미지를 저장

    # ------------ 이미지 생성  ------------
    unique_filename = f"{uuid.uuid4()}_{origin_image.filename}"

    origin_ad_image_path = ORIGIN_AD_IMAGE_DIR / unique_filename

    try: 
        with open(origin_ad_image_path, "wb") as buffer:
            shutil.copyfileobj(origin_image.file, buffer)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to save origin image file: {e}")

    response = generate_ad_image(category, origin_ad_image_path)

    if response is None:
        raise HTTPException(status_code=500, detail="Failed to generate ad image")
    
    # ------------ 이미지 생성 결과 확인 ------------

    generated_ad_image_path = GENERATED_AD_IMAGE_DIR / unique_filename

    image_save_flag = False

    for part in response.candidates[0].content.parts:
        if part.text is not None:
            print(part.text)
        elif part.inline_data is not None:
            image = Image.open(BytesIO(part.inline_data.data))

            unique_filename = f"{uuid.uuid4()}_{category}.png"
            generated_ad_image_path = GENERATED_AD_IMAGE_DIR / unique_filename
            
            image.save(generated_ad_image_path)
            image_save_flag =True

    if image_save_flag == False:
        raise HTTPException(status_code=500, detail="Failed to save generated ad image")
    
    return JSONResponse(content={"message": "AD image generated successfully.", "image_path": Path(generated_ad_image_path).as_posix()},
                                status_code=200)




# -----------------------------------------------------------       
# 광고 업체가 이미지 확인하고 자신의 정보 등록
@register_router.post("/ad/register")
async def register_ad_api(
    save_image_path: str,
    company: str,
    product: str,
    category: str
):
    """
    생성된 광고 이미지와 관련 데이터를 JSON 파일에 저장합니다.
    """
    # 1. 파일 경로 설정
    json_file_path = AD_DATA_FILE

    # 2. 기존 json 데이터 읽기(파일이 없으면 빈 리스트로 초기화)
    try:
        with open(json_file_path, 'r', encoding="utf-8") as f:
            data = json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        data = []
    
    # 3. 새로운 데이터 객체 생성
    max_id = max((item["id"] for item in data), default=0)

    new_entity = {
        "id": max_id + 1,
        "company": company,
        "product": product,
        "category": category,
        "image_path": save_image_path
    }

    data.append(new_entity)

    # 5. 변경된 데이터를 json 파일에 쓰기
    with open(json_file_path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=4, ensure_ascii=False)
    
    return JSONResponse(content={"message":f"새로운 데이터가 '{Path(json_file_path).as_posix()}' 파일에 추가되었습니다."}, status_code=200)




# -----------------------------------------------------------
# 광고 업체가 이미제에 로고를 삽입
@register_router.post("/ad/logo")
async def insert_logo_api(
    logo_image : UploadFile = File(...),
    ad_id: int = Form(...)
):
    """
    광고 이미지에 로고를 삽입하고, JSON 데이터의 이미지 경로를 업데이트합니다.
    
    Args:
        logo_image (UploadFile): 삽입할 로고 이미지 파일
        ad_id (int): 광고 이미지 데이터를 찾기 위한 ID
    """
    # 1. json 데이터에서 광고 이미지 경로를 가져오기
    try:
        with open(AD_DATA_FILE, 'r', encoding="utf-8") as f:
            ad_data = json.load(f)
    except FileNotFoundError:
        raise HTTPException(status_code=500, detail=f"Ad data file not found at {AD_DATA_FILE}")

    # ad_id와 일치하는 데이터를 찾습니다.
    ad_info = next((ad for ad in ad_data if ad["id"] == ad_id), None)

    if ad_info is None:
        raise HTTPException(status_code=404, detail=f"Ad with ID {ad_id} not found.")

    image_path_str = ad_info["image_path"]

    # 2. 업로드된 로고 이미지를 서버에 저장
    logo_filename = f"{uuid.uuid4()}_{logo_image.filename}"
    logo_path = LOGO_DIR / logo_filename

    try:
        with open(logo_path, "wb") as buffer:
            shutil.copyfileobj(logo_image.file, buffer)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to save logo image: {e}")
    
    # 3. 로고를 광고 이미지에 합성
    merged_image = insert_logo_to_image(image_path_str, str(logo_path))
    
    # 5. 로고가 합성된 새 이미지를 저장함
    new_filename = f"with_logo_{Path(ad_info['image_path']).stem}.png"
    new_image_path = GENERATED_AD_IMAGE_DIR / new_filename
    cv2.imwrite(str(new_image_path), merged_image)

    # 6. JSON 파일의 image_path 업데이트
    for ad in ad_data:
        if ad["id"] == ad_id:
            ad["image_path"] = Path(new_image_path).as_posix()
            break
    
    with open(AD_DATA_FILE, "w", encoding="utf-8") as f:
        json.dump(ad_data, f, indent=4, ensure_ascii=False)

    # 7. 성공의 응답 반환
    return JSONResponse(content={"message": "Logo is successfully inserted and ad_data updated.",
            "image_path": Path(new_image_path).as_posix()},
            status_code=200)

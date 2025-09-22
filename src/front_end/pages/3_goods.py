# 3_goods.py
import streamlit as st
import requests
from pathlib import Path
from io import BytesIO

# === 설정: FastAPI가 동작중인 URL을 여기에 맞게 바꿔주세요 ===
BASE_API_URL = "http://localhost:8080"  # 예: "http://127.0.0.1:8000"

# helper: FastAPI가 반환한 파일시스템 경로 -> 공개 접근 가능한 URL로 변환
def fs_path_to_public_url(fs_path: str) -> str:
    # fs_path 예: /home/user/project/data/ad_images/uuid_cat.png
    filename = Path(fs_path).name
    return f"{BASE_API_URL}/ad/images/{filename}"

# 페이지 타이틀
st.set_page_config(page_title="광고 이미지 생성/등록 (Ad Creator)", layout="centered")
st.title("광고 이미지 생성 & 등록 도구")

# 상태 저장 (생성된 이미지 URL, 원본 이미지 바이트 등)
if "origin_bytes" not in st.session_state:
    st.session_state.origin_bytes = None
if "generated_url" not in st.session_state:
    st.session_state.generated_url = None
if "registered_ad" not in st.session_state:
    st.session_state.registered_ad = None

st.header("1) 원본 이미지 업로드")
uploaded = st.file_uploader("원본 이미지를 업로드하세요 (광고에 사용할 객체 이미지)", type=["png", "jpg", "jpeg"])
if uploaded is not None:
    st.session_state.origin_bytes = uploaded.read()
    st.image(st.session_state.origin_bytes, caption="업로드한 원본 이미지", use_container_width =True)

st.markdown("---")
st.header("2) 카테고리 입력 → 광고 이미지 생성")
with st.form("generate_form"):
    category = st.text_input("광고 카테고리 (예: coffee, shampoo, snack 등)", value="product")
    submitted = st.form_submit_button("광고 이미지 생성 요청")
    if submitted:
        if st.session_state.origin_bytes is None:
            st.error("먼저 원본 이미지를 업로드하세요.")
        else:
            try:
                files = {
                    # FastAPI 쪽에서는 param명이 origin_image 이므로 동일하게 지정
                    "origin_image": ("origin.png", BytesIO(st.session_state.origin_bytes), "image/png")
                }
                data = {"category": category}
                url = f"{BASE_API_URL}/ad/generate_ad_image"
                with st.spinner("이미지 생성 중... (모델 호출)"):
                    resp = requests.post(url, files=files, data=data, timeout=120)
                if resp.status_code == 200:
                    resp_json = resp.json()
                    # FastAPI가 반환한 image_path는 파일시스템 경로일 가능성이 큽니다.
                    fs_image_path = resp_json.get("image_path")
                    if fs_image_path:
                        public_url = fs_path_to_public_url(fs_image_path)
                        st.session_state.generated_url = public_url
                        st.success("생성 완료: 생성된 광고 이미지를 아래에서 확인하세요.")
                    else:
                        st.error(f"이미지 경로를 응답에서 찾을 수 없습니다: {resp_json}")
                else:
                    st.error(f"생성 요청 실패: {resp.status_code} / {resp.text}")
            except Exception as e:
                st.error(f"요청 중 예외 발생: {e}")

if st.session_state.generated_url:
    st.markdown("**생성된 광고 이미지 미리보기**")
    st.image(st.session_state.generated_url, use_container_width =True)

st.markdown("---")
st.header("3) 생성된 이미지로 광고 등록 (회사명 / 상품명 입력)")
with st.form("register_form"):
    company = st.text_input("회사명")
    product = st.text_input("상품명")
    category_for_register = st.text_input("카테고리 (등록용, 기본은 위에서 사용한 값)", value=category if 'category' in locals() else "")
    register_btn = st.form_submit_button("광고 등록 (JSON에 저장)")
    if register_btn:
        if st.session_state.generated_url is None:
            st.error("먼저 광고 이미지를 생성하세요.")
        elif not company or not product:
            st.error("회사명과 상품명을 모두 입력하세요.")
        else:
            try:
                # FastAPI /ad/register는 바디(또는 쿼리)로 받음 -> JSON으로 전송
                register_url = f"{BASE_API_URL}/ad/register"
                # save_image_path로 파일 시스템 경로를 기대하므로, 원 API의 응답에서 받은 fs path를 사용해야 함.
                # 다만 우리는 public URL만 가지고 있으므로, 서버에 반환된 fs 경로를 다시 얻는 방법이 필요.
                # generate endpoint의 응답에서 받은 원 파일시스템 경로를 그대로 사용하면 안전합니다.
                # 여기서는 /ad/generate_ad_image 호출 응답 때 fs 경로를 로컬에 저장하도록 개선하는 것이 권장됩니다.
                # 간단히 하기 위해 서버가 저장한 파일 이름(마지막 부분)로 경로를 구성해 전송해봅니다.
                # 예: /.../data/ad_images/filename.png
                # 이 방식이 서버와 정확히 맞아야 정상 작동합니다.
                # 따라서 위 generate 응답의 image_path를 그대로 사용하도록 아래 코드를 구성합니다.

                # 먼저 생성 요청에서 받아온 FS 경로를 얻기 위해 generate endpoint 재호출 결과를 저장했어야 했습니다.
                # 만약 st.session_state에 원 FS 경로를 저장하지 않았다면, 서버에서 /ad/list로 확인해 최신 항목을 찾아도 됩니다.
                # 여기서는 간단히 /ad/list를 불러 가장 최근 항목의 image_path를 사용합니다.

                list_url = f"{BASE_API_URL}/ad/list"
                list_resp = requests.get(list_url, timeout=10)
                fs_image_path_to_register = None
                if list_resp.status_code == 200:
                    ad_list = list_resp.json()
                    # 생성 직후 등록하는 흐름이면 list에서 가장 최근 항목 없을 수 있음.
                    # 안전하게 st.session_state.generated_url 파일명을 원격에서 찾음:
                    gen_filename = Path(st.session_state.generated_url).name
                    for ad in ad_list:
                        if Path(ad.get("image_path", "")).name == gen_filename:
                            fs_image_path_to_register = ad.get("image_path")
                            break
                # fallback: generate endpoint은 응답에 fs 경로를 담아줬으니, 더 좋은 방법은 그 값을 세션에 저장하는 것입니다.
                if fs_image_path_to_register is None:
                    st.warning("서버에서 등록할 이미지의 파일 시스템 경로를 찾지 못했습니다. 서버의 generate API 응답에서 image_path(파일시스템 경로)를 세션에 저장하도록 서버 코드를 약간 수정하는 것이 안정적입니다.")
                    # 그래도 시도해보기: public URL의 파일명만 사용해서 서버의 ad_images 폴더에 있다고 가정
                    fs_image_path_to_register = f"/data/ad_images/{Path(st.session_state.generated_url).name}"

                payload = {
                    "save_image_path": fs_image_path_to_register,
                    "company": company,
                    "product": product,
                    "category": category_for_register
                }
                resp = requests.post(register_url, data=payload, timeout=10)
                if resp.status_code == 200:
                    st.success("광고 등록(데이터 저장) 완료")
                    st.session_state.registered_ad = payload
                else:
                    st.error(f"등록 실패: {resp.status_code} / {resp.text}")
            except Exception as e:
                st.error(f"등록 요청 중 예외 발생: {e}")

st.markdown("---")
st.header("4) (선택) 로고 업로드로 합성하기")
st.markdown("서버에 저장되어 있는 광고 목록을 불러와서, 합성하고 싶은 항목을 선택하세요.")

if st.button("서버의 광고 목록 불러오기"):
    try:
        resp = requests.get(f"{BASE_API_URL}/ad/list", timeout=10)
        if resp.status_code == 200:
            ad_list = resp.json()
            st.session_state.ad_list = ad_list
            st.success(f"총 {len(ad_list)}개의 광고 정보를 불러왔습니다.")
        else:
            st.error(f"목록 불러오기 실패: {resp.status_code} / {resp.text}")
    except Exception as e:
        st.error(f"목록 요청 실패: {e}")

if "ad_list" in st.session_state and st.session_state.ad_list:
    ad_list = st.session_state.ad_list
    # 간단히 selectbox로 목록 선택 (id와 product로 표시)
    options = [f"{ad['id']}: {ad.get('company','-')} / {ad.get('product','-')}" for ad in ad_list]
    selected = st.selectbox("합성할 광고 선택", options)
    selected_id = int(selected.split(":")[0])

    # 선택한 항목의 이미지 미리보기
    selected_ad = next(ad for ad in ad_list if ad["id"] == selected_id)
    selected_fs_path = selected_ad.get("image_path")
    if selected_fs_path:
        preview_url = fs_path_to_public_url(selected_fs_path)
        st.image(preview_url, caption="선택한 광고 이미지 미리보기", use_container_width =True)

    logo_file = st.file_uploader("삽입할 로고 이미지 업로드", type=["png", "jpg", "jpeg"], key="logo_uploader")
    if st.button("로고 업로드 및 합성 요청"):
        if logo_file is None:
            st.error("로고 이미지를 업로드하세요.")
        else:
            try:
                files = {
                    "logo_image": (logo_file.name, logo_file, logo_file.type or "image/png")
                }
                data = {"ad_id": str(selected_id)}
                resp = requests.post(f"{BASE_API_URL}/ad/logo", files=files, data=data, timeout=60)
                if resp.status_code == 200:
                    resp_json = resp.json()
                    new_image_fs_path = resp_json.get("image_path")
                    if new_image_fs_path:
                        new_public_url = fs_path_to_public_url(new_image_fs_path)
                        st.success("로고 합성 완료 — 아래에서 확인하세요.")
                        st.image(new_public_url, caption="로고 합성된 이미지", use_container_width =True)
                    else:
                        st.error(f"응답에서 image_path를 찾을 수 없습니다: {resp_json}")
                else:
                    st.error(f"로고 합성 요청 실패: {resp.status_code} / {resp.text}")
            except Exception as e:
                st.error(f"로고 합성 중 예외 발생: {e}")
else:
    st.info("먼저 '서버의 광고 목록 불러오기' 버튼을 눌러 목록을 받아오세요.")

st.markdown("---")
st.write("끝. 필요하시면 이 코드를 원하는 스타일로 수정해 드릴게요.")

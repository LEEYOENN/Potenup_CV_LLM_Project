# run_app/pages/1_select_image.py
import streamlit as st
import requests

st.set_page_config(page_title="영상 등록", layout="wide")

# -----------------------------
# CSS (심플)
# -----------------------------
st.markdown("""
<style>
/* 파일 업로더 글씨 색상 */
[data-testid="stFileUploader"] label {
    color: white !important;
    font-weight: 1000;
}

/* number_input 레이블 색상 */
[data-testid="stNumberInputContainer"] label {
    color: white !important;
    font-weight: 1000;
}

/* 입력 필드 텍스트 색상 */
[data-testid="stFileUploader"] div, 
[data-baseweb="input"] input {
    color: white !important;
}
</style>
""", unsafe_allow_html=True)

# -----------------------------
# 본문: 영상 업로드 + 숫자 입력
# -----------------------------
video_file = st.file_uploader("🎥 영상 업로드", type=["mp4", "mov", "avi", "mkv"])
show_time = st.number_input("광고 노출 시간(초)", min_value=0, step=1)

st.divider()

image_file = st.file_uploader("광고 이미지 업로드(옵션)", type=["jpg", "jpeg", "png"])
goods_keyword = st.text_input("광고 키워드(옵션)")
goods_link = st.text_input("광고 링크(옵션)")


# -----------------------------
# 전송 버튼
# -----------------------------
if st.button("광고 추가 영상으로 변환", type="primary"):
    if not video_file:
        st.warning("영상을 업로드해주세요.")
    else:
        try:
            
            files = {
                "video": (video_file.name, video_file, video_file.type),
                "image": (image_file.name, image_file, image_file.type)    
            }
            datas = {"show_time": show_time, "goods_keyword": goods_keyword, "goods_link" : goods_link}
            
            with st.spinner("서버로 전송 중..."):
                url = "http://localhost:8000/video/stt"
                res = requests.post(url, files=files, data=datas)
                res.raise_for_status()
                data = res.json()

            st.success("영상 변환 성공 ✅")
            st.json(data)

        except Exception as e:
            st.error(f"영상 변환 실패: {e}")


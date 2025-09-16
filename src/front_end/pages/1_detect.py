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
    color: black !important;
    font-weight: 600;
}

/* number_input 레이블 색상 */
[data-testid="stNumberInputContainer"] label {
    color: black !important;
    font-weight: 600;
}

/* 입력 필드 텍스트 색상 */
[data-testid="stFileUploader"] div, 
[data-baseweb="input"] input {
    color: black !important;
}
</style>
""", unsafe_allow_html=True)

# TODO 원하는대로 입력은 바꾸셔요
# -----------------------------
# 본문: 영상 업로드 + 숫자 입력 
# -----------------------------
video_file = st.file_uploader("🎥 영상 업로드", type=["mp4", "mov", "avi", "mkv"])
show_time = st.number_input("숫자 값을 입력하세요", min_value=0, step=1)

# -----------------------------
# 전송 버튼
# -----------------------------
if st.button("전송", type="primary"):
    if not video_file:
        st.warning("영상을 업로드해주세요.")
    else:
        try:
            show_time = {"number": show_time}
            video = {"file": (video_file.name, video_file, video_file.type)}
            
            with st.spinner("서버로 전송 중..."):
                url = "http://localhost:8000/video/detect"
                res = requests.post(url, data=show_time, files=video, timeout=(5, 600))
                res.raise_for_status()
                data = res.json()
                
            st.success("서버 응답 성공 ✅")
            st.json(data)

        except Exception as e:
            st.error(f"API 호출 실패: {e}")

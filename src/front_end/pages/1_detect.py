# 1_detect.py (최종 수정 버전)
import streamlit as st
import requests
from pathlib import Path
from io import BytesIO

BASE_API_URL = "http://localhost:8080"  # FastAPI 주소/포트에 맞게 변경

st.set_page_config(page_title="동영상에 광고 삽입", layout="wide")
st.title("동영상에 광고 삽입 도구")

def fs_path_to_ad_public_url(fs_path: str) -> str:
    filename = Path(fs_path).name
    return f"{BASE_API_URL}/ad/images/{filename}"

# 광고 목록 불러오기
st.header("1) 서버에 저장된 광고 목록 불러오기")
if st.button("광고 목록 불러오기"):
    try:
        resp = requests.get(f"{BASE_API_URL}/ad/list", timeout=10)
        #st.write("GET /ad/list 응답 코드:", resp.status_code)
        #st.write(resp.text[:2000])  # 응답 일부 출력 (길면 잘림)
        if resp.status_code == 200:
            st.session_state.ad_list = resp.json()
            st.success(f"광고 {len(st.session_state.ad_list)}건을 불러왔습니다.")
        else:
            st.error(f"목록 불러오기 실패: {resp.status_code} / {resp.text}")
    except Exception as e:
        st.error(f"목록 요청 중 오류: {e}")

col1, col2 = st.columns([1, 1.2])

with col1:
    st.subheader("2) 유튜버 : 동영상 업로드")
    uploaded_video = st.file_uploader("업로드할 영상 파일 선택 (mp4 권장)", type=["mp4", "mov", "mkv", "avi"])
    if uploaded_video is not None:
        st.info(f"업로드 완료: {uploaded_video.name} ({uploaded_video.type})")

    st.markdown("---")
    st.subheader("3) 삽입할 광고 선택")
    if "ad_list" in st.session_state and st.session_state.ad_list:
        options = [f"{ad['id']} | {ad.get('company','-')} / {ad.get('product','-')}" for ad in st.session_state.ad_list]
        selection = st.selectbox("광고 아이템 선택", options)
        selected_id = int(selection.split("|")[0].strip())
        selected_ad = next(ad for ad in st.session_state.ad_list if ad["id"] == selected_id)
        if selected_ad.get("image_path"):
            img_url = fs_path_to_ad_public_url(selected_ad["image_path"])
            st.image(img_url, caption=f"선택된 광고: {selected_ad.get('product','-')}", use_container_width=True)
        else:
            st.info("선택된 광고에 이미지 경로가 없습니다.")
    else:
        st.info("먼저 '광고 목록 불러오기' 버튼을 눌러 광고 목록을 가져오세요.")

    st.markdown("---")
    st.subheader("4) 광고 삽입 실행")
    # 광고 삽입 실행 버튼 클릭 핸들 (수정된 로직)
    if st.button("광고 삽입 실행"):
        if uploaded_video is None:
            st.error("먼저 동영상을 업로드하세요.")
        elif "ad_list" not in st.session_state or not st.session_state.ad_list:
            st.error("먼저 광고 목록을 불러오고 삽입할 광고를 선택하세요.")
        else:
            try:
                files = {
                    "video_file": (uploaded_video.name, uploaded_video, uploaded_video.type or "video/mp4")
                }
                data = {"ad_id": str(selected_id)}
                with st.spinner("서버에 업로드하고 광고를 삽입하는 중입니다. (처리 시간이 오래 걸릴 수 있습니다)"):
                    resp = requests.post(f"{BASE_API_URL}/video/ad_attach", files=files, data=data, timeout=300)

                #st.write("POST /video/ad_attach 응답 상태:", resp.status_code)
                #st.write("서버 응답(일부):", resp.text[:2000])

                if resp.status_code == 200:
                    resp_json = resp.json()
                    public_url = resp_json.get("public_url")
                    
                    if public_url:
                        full_public_url = f"{BASE_API_URL}{public_url}"
                        st.session_state.last_processed_video_url = full_public_url
                        
                        st.success("서버 처리 완료! 동영상을 다운로드 중입니다...")
                        with st.spinner("동영상 파일을 다운로드 중..."):
                            video_response = requests.get(full_public_url, timeout=60)
                            
                            if video_response.status_code == 200:
                                st.session_state.last_processed_video_bytes = video_response.content
                                st.success("동영상 다운로드 완료. 위에서 재생됩니다.")
                            else:
                                st.error(f"동영상 다운로드 실패: HTTP {video_response.status_code}")
                                st.info("브라우저에서 직접 열어 확인해보세요: " + full_public_url)
                    else:
                        st.error("서버 응답에 public_url이 없습니다. 서버 코드를 확인하세요.")
                else:
                    st.error(f"서버 처리 실패: {resp.status_code} / {resp.text}")
            except Exception as e:
                st.error(f"요청 중 예외 발생: {e}")

with col2:
    st.subheader("결과 미리보기 / 재생")
    if "last_processed_video_bytes" in st.session_state and st.session_state.last_processed_video_bytes:
        try:
            st.video(st.session_state.last_processed_video_bytes)
            st.info("동영상 재생: 바이트 스트림 사용")
        except Exception:
            st.error("바이트 스트림 재생 중 오류 발생.")
    elif "last_processed_video_url" in st.session_state and st.session_state.last_processed_video_url:
        st.write("public URL:", st.session_state.last_processed_video_url)
        st.info("동영상이 다운로드되지 않았습니다. '광고 삽입 실행' 버튼을 다시 눌러주세요.")
    else:
        st.info("아직 처리된 동영상이 없습니다.")

st.markdown("---")
# st.write("디버깅 팁:")
# st.write("- `GET` 요청 시 **타임아웃(timeout)** 시간을 충분히 늘려주세요. (대용량 영상일 경우 특히 중요)")
# st.write("- 브라우저의 개발자 도구(F12) 네트워크 탭에서 `processed_videos` URL의 응답을 확인하여 파일이 제대로 전송되는지 검사하세요.")
# st.write("- 서버(uvicorn) 로그에 `GET` 요청이 `200` OK 또는 `206` Partial Content로 정상적으로 처리되는지 확인하세요.")
# st.write("- FastAPI가 **`StaticFiles`**를 사용하여 `processed_videos` 폴더를 제대로 마운트했는지 재확인하세요.")


### Step 2: Elicit Fact

#이 코드를 실행한 후, 여전히 재생이 되지 않는다면 서버의 FastAPI 코드에서 `processed_videos` 폴더를 어떻게 마운트했는지 그 부분을 보여주시겠어요?
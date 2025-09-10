from faster_whisper import WhisperModel
from pathlib import Path

# TODO 자막 추출 할 때 쓰기 좋은 형태로 생성하는 것으로 변경(한줄에 한 자막 - uuid, 시간, 텍스트)
# 68c16153-df74-8329-9778-1b3d05140df8, 00:00:00 --> 00:00:01, 살까요? 말까요?
def srt_ts(t: float) -> str:

    ms = int(t * 1000)
    hh, ms = divmod(ms, 3600000)
    mm, ms = divmod(ms, 60000)
    ss, ms = divmod(ms, 1000)

    return f"{hh:02d}:{mm:02d}:{ss:02d},{ms:03d}"

m = WhisperModel("small", device="cpu", compute_type="int8")
segments, info = m.transcribe("./video/joo.mp4", language="ko", vad_filter=False)

out = Path("out"); out.mkdir(exist_ok=True)
txt_path = out / "joo.txt"
srt_path = out / "joo.srt"

with open(txt_path, "w", encoding="utf-8") as f_txt, open(srt_path, "w", encoding="utf-8") as f_srt:
    for i, s in enumerate(segments, start=1):   
        line = s.text.strip()
        f_txt.write(line + "\n")
        f_srt.write(f"{i}\n{srt_ts(s.start)} --> {srt_ts(s.end)}\n{line}\n")

print("saved:", txt_path, srt_path)
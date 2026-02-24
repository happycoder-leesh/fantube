import yt_dlp
import whisper
import os

# ─── 설정 (여기만 수정) ──────────────────
VIDEO_URL = "https://www.youtube.com/watch?v=THGAZDSqVzg"
OUTPUT_DIR = "./audio"
RESULT_DIR = "./results"
# ─────────────────────────────────────────

os.makedirs(OUTPUT_DIR, exist_ok=True)
os.makedirs(RESULT_DIR, exist_ok=True)

print("▶ 음성 다운로드 중...")
ydl_opts = {
    'outtmpl': f'{OUTPUT_DIR}/%(title)s.%(ext)s',
    'format': 'bestaudio/best',
    'postprocessors': [{
        'key': 'FFmpegExtractAudio',
        'preferredcodec': 'mp3',
        'preferredquality': '192',
    }],
    'writesubtitles': True,
    'writeautomaticsub': True,
    'subtitleslangs': ['ko'],
}
with yt_dlp.YoutubeDL(ydl_opts) as ydl:
    info = ydl.extract_info(VIDEO_URL, download=True)
    video_title = info.get('title', 'unknown')

# 실제 다운로드된 mp3 파일 자동 탐색
audio_path = None
for f in os.listdir(OUTPUT_DIR):
    if f.endswith('.mp3'):
        audio_path = os.path.join(OUTPUT_DIR, f)
        break

if not audio_path:
    raise FileNotFoundError("mp3 파일을 찾을 수 없습니다. audio 폴더 확인하세요.")

print(f"✓ 다운로드 완료: {audio_path}")

# 2. Whisper 자막 추출
print("▶ 자막 추출 중... (시간 걸림)")
model = whisper.load_model("large-v3")
result = model.transcribe(
    audio_path,
    language="ko",
    verbose=True,
    condition_on_previous_text=False,
    no_speech_threshold=0.6,
    temperature=0.0
)

# 반복 제거 후처리
def remove_repetitions(segments, repeat_threshold=3):
    cleaned = []
    prev_texts = []
    
    for seg in segments:
        text = seg['text'].strip()
        
        # 최근 N개 중 같은 텍스트가 threshold 이상이면 스킵
        if prev_texts.count(text) >= repeat_threshold:
            continue
        
        cleaned.append(seg)
        prev_texts.append(text)
        
        # 최근 10개만 유지
        if len(prev_texts) > 10:
            prev_texts.pop(0)
    
    return cleaned

# 후처리 적용
print("▶ 반복 구간 제거 중...")
cleaned_segments = remove_repetitions(result["segments"], repeat_threshold=3)
removed_count = len(result["segments"]) - len(cleaned_segments)
print(f"✓ {removed_count}개 반복 구간 제거됨")

# 3. 결과 저장
output_path = f"{RESULT_DIR}/{video_title}_transcript.txt"
with open(output_path, "w", encoding="utf-8") as f:
    f.write(f"영상 제목: {video_title}\n")
    f.write(f"총 길이: {int(cleaned_segments[-1]['end']//60)}분\n")
    f.write(f"반복 제거: {removed_count}개 구간\n")
    f.write("="*50 + "\n\n")
    for seg in cleaned_segments:
        start = f"{int(seg['start']//60):02d}:{int(seg['start']%60):02d}"
        end   = f"{int(seg['end']//60):02d}:{int(seg['end']%60):02d}"
        f.write(f"[{start} ~ {end}] {seg['text'].strip()}\n")

print(f"\n✓ 완료! 결과 파일: {output_path}")
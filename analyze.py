import anthropic
import os
import json

# ─── 설정 ───────────────────────────────
RESULT_DIR = "./results"
OUTPUT_DIR = "./analyzed"
# ────────────────────────────────────────

os.makedirs(OUTPUT_DIR, exist_ok=True)

def load_transcript(txt_path):
    with open(txt_path, "r", encoding="utf-8") as f:
        return f.read()

def analyze_transcript(transcript_text, video_title):
    client = anthropic.Anthropic(api_key=os.environ.get("ANTHROPIC_API_KEY"))
    
    MAX_CHARS = 6000
    if len(transcript_text) > MAX_CHARS:
        transcript_text = transcript_text[:MAX_CHARS]
        print(f"⚠️ 자막이 길어서 앞 {MAX_CHARS}자만 분석합니다.")
    
    prompt = f"""
아래는 NMIXX(엔믹스) 자체 컨텐츠 영상의 자막이야. 타임스탬프가 포함되어 있어.

다음 기준으로 유튜브 쇼츠 후보 구간을 분석해줘:

[분석 기준]
1. 멤버 반응이 과장되거나 예상치 못한 발언이 있는 구간
2. 웃음이 터지거나 분위기가 급반전되는 구간
3. 특정 멤버의 캐릭터가 잘 드러나는 구간
4. 팬이 아니어도 클릭할 수 있는 범용적인 구간
5. 다른 영상과 엮을 수 있을 것 같은 구간

[태그 카테고리]
- 멤버: 해원, 배이, 지니, 설윤, 규진, 릴리, 전체
- 반응유형: 과반응, 예상치못한발언, 티격태격, 언어유희, 반전, 감동, 당황
- 상황: 요리, 게임, 토크, 야외, 댄스, 먹방
- 활용: 단독클립가능, 엮기가능, 인트로적합, 아웃트로적합
- 우선순위: 상, 중, 하

[우선순위 기준 - 엄격하게 적용]
- 상: 팬이 아니어도 웃기거나 궁금한 장면. 전체 영상에서 3~5개만
- 중: 팬이라면 재밌는 장면. 전체 영상에서 5~8개
- 하: 그 외. 가능하면 하는 결과에 포함하지 마.

전체 영상에서 우선순위 "상" 은 최대 5개만 뽑아줘.

[태그 규칙]
- 멤버 전원이 관련된 장면은 "전체"만 태그
- 특정 멤버가 주인공인 장면만 개인 이름 태그
- "전체"와 개인 이름을 동시에 태그하지 마

반드시 아래 JSON 형식으로만 답해줘. 다른 텍스트 없이 JSON만:

{{
  "video_title": "{video_title}",
  "clips": [
    {{
      "start": "MM:SS",
      "end": "MM:SS",
      "text": "해당 구간 핵심 대사",
      "tags": {{
        "멤버": [],
        "반응유형": [],
        "상황": [],
        "활용": [],
        "우선순위": "상/중/하"
      }},
      "reason": "쇼츠 추천 이유",
      "title_suggestion": "추천 제목 후보 2개를 리스트로"
    }}
  ]
}}

[자막]
{transcript_text}
"""

    response = client.messages.create(
        model="claude-sonnet-4-6",
        max_tokens=8000,
        messages=[{"role": "user", "content": prompt}]
    )
    
    return response.content[0].text

def save_result(result_text, video_title):
    # JSON 파싱
    try:
        # 혹시 ```json ``` 감싸진 경우 제거
        clean = result_text.strip()
        if clean.startswith("```"):
            clean = clean.split("```")[1]
            if clean.startswith("json"):
                clean = clean[4:]
        
        data = json.loads(clean)
        
        # JSON 저장
        output_path = f"{OUTPUT_DIR}/{video_title}_analyzed.json"
        with open(output_path, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        
        print(f"✓ 분석 완료: {output_path}")
        print(f"✓ 쇼츠 후보 {len(data['clips'])}개 추출됨\n")
        
        # 요약 출력
        for i, clip in enumerate(data["clips"], 1):
            print(f"[{i}] {clip['start']} ~ {clip['end']}")
            print(f"    대사: {clip['text']}")
            print(f"    멤버: {', '.join(clip['tags']['멤버'])}")
            print(f"    우선순위: {clip['tags']['우선순위']}")
            print(f"    이유: {clip['reason']}")
            print(f"    제목 후보: {clip['title_suggestion']}")
            print()
            
    except json.JSONDecodeError as e:
        print(f"JSON 파싱 실패: {e}")
        # 원본 텍스트 저장
        output_path = f"{OUTPUT_DIR}/{video_title}_raw.txt"
        with open(output_path, "w", encoding="utf-8") as f:
            f.write(result_text)
        print(f"원본 텍스트 저장됨: {output_path}")

# ─── 실행 ───────────────────────────────
# results 폴더에서 가장 최근 txt 파일 자동 선택
txt_files = [f for f in os.listdir(RESULT_DIR) if f.endswith("_transcript.txt")]

if not txt_files:
    raise FileNotFoundError("results/ 폴더에 transcript.txt 파일이 없습니다.")

video_titles = list(dict.fromkeys([
    f.replace("_transcript_part1.txt", "")
     .replace("_transcript_part2.txt", "")
     .replace("_transcript_part3.txt", "")
     .split("_transcript_part")[0]
    for f in txt_files
]))

for video_title in video_titles:
    # 해당 영상의 청크 파일 모두 수집
    part_files = sorted([
        f for f in txt_files 
        if f.startswith(video_title) and "_transcript_part" in f
    ])
    
    print(f"\n▶ 분석 시작: {video_title}")
    print(f"▶ 총 {len(part_files)}개 파트 처리")
    
    all_clips = []
    
    for part_file in part_files:
        txt_path = os.path.join(RESULT_DIR, part_file)
        print(f"  → {part_file} 분석 중...")
        
        transcript = load_transcript(txt_path)
        result = analyze_transcript(transcript, video_title)
        
        # JSON 파싱해서 clips만 추출
        try:
            clean = result.strip()
            if clean.startswith("```"):
                clean = clean.split("```")[1]
                if clean.startswith("json"):
                    clean = clean[4:]
            data = json.loads(clean)
            all_clips.extend(data.get("clips", []))
            print(f"  ✓ {len(data.get('clips', []))}개 클립 추출")
        except json.JSONDecodeError as e:
            print(f"  ⚠️ 파싱 실패: {e}")
    
    # 전체 결과 저장
    final_data = {
        "video_title": video_title,
        "total_clips": len(all_clips),
        "clips": all_clips
    }
    save_result(json.dumps(final_data, ensure_ascii=False), video_title)
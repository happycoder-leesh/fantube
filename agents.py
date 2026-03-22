import anthropic
import os
import json

client = anthropic.Anthropic(api_key=os.environ.get("ANTHROPIC_API_KEY"))
MODEL = "claude-sonnet-4-6"


def safe_json_parse(text, max_tokens_hint=""):
    """JSON 파싱 안전하게 처리"""
    try:
        # ``` 제거
        clean = text.strip()
        if clean.startswith("```"):
            clean = clean.split("```")[1]
            if clean.startswith("json"):
                clean = clean[4:]
        clean = clean.strip()
        
        # 정상 파싱 시도
        return json.loads(clean)
    
    except json.JSONDecodeError:
        # 잘린 JSON 복구 시도
        # 열린 괄호/따옴표 개수 맞춰서 닫기
        open_braces  = clean.count("{") - clean.count("}")
        open_brackets = clean.count("[") - clean.count("]")
        
        # 마지막 불완전한 줄 제거
        lines = clean.split("\n")
        while lines:
            last = lines[-1].strip()
            if last and not last.endswith((",", "{", "[", "}", "]")):
                lines.pop()
            else:
                break
        
        clean = "\n".join(lines)
        
        # 닫는 괄호 추가
        clean += "]" * open_brackets
        clean += "}" * open_braces
        
        try:
            result = json.loads(clean)
            print("  ⚠️ JSON 일부 복구됨 (잘린 응답)")
            return result
        except json.JSONDecodeError as e:
            print(f"  ❌ JSON 복구 실패: {e}")
            print(f"  원본 텍스트:\n{text[:500]}")
            raise


# ─────────────────────────────────────────
# Agent 1: 쇼츠 기획자
# ─────────────────────────────────────────
def agent_planner(transcript_text):
    print("\n🎬 [Agent 1 - 쇼츠 기획자] 기획 중...")
    
    prompt = f"""
너는 K-POP 팬튜브 쇼츠 전문 기획자야.
NMIXX(엔믹스) 자체 컨텐츠 자막을 보고 쇼츠 기획 방향을 잡아줘.

[기획 원칙]
- 팬이 아니어도 클릭할 수 있는 범용성 우선
- 멤버 간 케미/반응 구도가 있는 장면 선호
- "이유", "순간", "반응" 포맷이 잘 터짐
- 18초 이하 짧은 클립은 비추천
- 특정 멤버 단독보다 멤버 간 상호작용 선호

[주의]
- 각 필드 값은 최대 50자 이내로 간결하게 작성
- preferred_formats 는 3개 이내
- key_members 는 2개 이내
- 불필요한 설명 없이 핵심만


아래 내용을 JSON으로만 답해줘:

{{
  "target_audience": "타겟 시청자 분석",
  "content_direction": "전체 콘텐츠 방향",
  "preferred_formats": ["추천 포맷 리스트"],
  "key_members": ["주목할 멤버와 이유"],
  "avoid": ["피해야 할 것들"],
  "expected_clips": "예상 추출 클립 수 (숫자만)"
}}

[자막]
{transcript_text}
"""
    
    response = client.messages.create(
        model=MODEL,
        max_tokens=3000,
        messages=[{"role": "user", "content": prompt}]
    )
    
    # result = response.content[0].text.strip()
    
    # # JSON 파싱
    # if result.startswith("```"):
    #     result = result.split("```")[1]
    #     if result.startswith("json"):
    #         result = result[4:]
    
    # plan = json.loads(result.strip())
    
    # agent_planner 파싱 부분
    plan = safe_json_parse(response.content[0].text)


    
    print(f"  ✓ 방향: {plan['content_direction']}")
    print(f"  ✓ 타겟: {plan['target_audience']}")
    return plan


# ─────────────────────────────────────────
# Agent 2: 영상 소스 추출자
# ─────────────────────────────────────────
def agent_extractor(transcript_text, plan):
    print("\n✂️  [Agent 2 - 영상 소스 추출자] 클립 추출 중...")
    
    prompt = f"""
너는 영상 편집 전문가야. 
기획자의 방향에 맞춰 자막에서 쇼츠 후보 클립을 추출해줘.

[기획자 방향]
- 타겟: {plan['target_audience']}
- 방향: {plan['content_direction']}
- 추천 포맷: {', '.join(plan['preferred_formats'])}
- 주목 멤버: {', '.join(plan['key_members'])}
- 피해야 할 것: {', '.join(plan['avoid'])}

[추출 기준]
- 기획 방향에 부합하는 구간 우선
- 타임스탬프 정확하게 기재
- 클립 길이는 30초~1분 이내 권장
- 멤버 태그는 주인공만 (전체면 "전체"만)
- 최대 10개까지만 추출

반드시 아래 JSON 형식으로만 답해줘:

{{
  "clips": [
    {{
      "start": "MM:SS",
      "end": "MM:SS",
      "text": "핵심 대사",
      "members": [],
      "reaction_type": "반응 유형",
      "situation": "상황",
      "reason": "추출 이유",
      "clip_score": 1~10
    }}
  ]
}}

[자막]
{transcript_text}
"""
    
    response = client.messages.create(
        model=MODEL,
        max_tokens=9000,
        messages=[{"role": "user", "content": prompt}]
    )
    
    # result = response.content[0].text.strip()
    
    # if result.startswith("```"):
    #     result = result.split("```")[1]
    #     if result.startswith("json"):
    #         result = result[4:]
    
    # clips_data = json.loads(result.strip())
    
    clips_data = safe_json_parse(response.content[0].text)
    
    print(f"  ✓ {len(clips_data['clips'])}개 클립 후보 추출")
    return clips_data


# ─────────────────────────────────────────
# Agent 3: 품질 검수자
# ─────────────────────────────────────────
def agent_reviewer(plan, clips_data, video_title):
    print("\n🔍 [Agent 3 - 품질 검수자] 최종 검수 중...")
    
    prompt = f"""
너는 유튜브 쇼츠 품질 검수 전문가야.
기획자의 방향과 추출된 클립을 대조해서 최종 승인 여부를 결정해줘.

[기획자 방향]
{json.dumps(plan, ensure_ascii=False, indent=2)}

[추출된 클립 후보]
{json.dumps(clips_data, ensure_ascii=False, indent=2)}

[검수 기준]
- 기획 방향과 일치하는가
- 팬이 아니어도 클릭할 수 있는가
- 클립 길이가 30초~1분 이내인가
- 우선순위 "상"은 최대 5개만 승인
- 멤버 태그가 정확한가 (전체 vs 개인 중복 금지)
- clip_score 7 이상만 우선순위 "상" 가능

반드시 아래 JSON 형식으로만 답해줘:

{{
  "video_title": "{video_title}",
  "review_summary": "전체 검수 총평",
  "total_approved": 승인된 클립 수,
  "clips": [
    {{
      "start": "MM:SS",
      "end": "MM:SS",
      "text": "핵심 대사",
      "tags": {{
        "멤버": [],
        "반응유형": [],
        "상황": [],
        "활용": [],
        "우선순위": "상/중/하"
      }},
      "reason": "최종 선정 이유",
      "title_suggestion": ["제목 후보1", "제목 후보2"],
      "approved": true/false,
      "reject_reason": "탈락 시 이유 (승인이면 null)"
    }}
  ]
}}
"""
    
    response = client.messages.create(
        model=MODEL,
        max_tokens=12000,
        messages=[{"role": "user", "content": prompt}]
    )
    
    # result = response.content[0].text.strip()
    
    # if result.startswith("```"):
    #     result = result.split("```")[1]
    #     if result.startswith("json"):
    #         result = result[4:]
    
    # final = json.loads(result.strip())
    final = safe_json_parse(response.content[0].text)
    
    approved = [c for c in final['clips'] if c['approved']]
    print(f"  ✓ 총 {len(clips_data['clips'])}개 중 {len(approved)}개 최종 승인")
    print(f"  ✓ 총평: {final['review_summary']}")
    return final


# ─────────────────────────────────────────
# 전체 파이프라인 실행
# ─────────────────────────────────────────
def run_agents(transcript_text, video_title):
    print(f"\n{'='*50}")
    print(f"📺 영상: {video_title}")
    print(f"{'='*50}")
    
    # 3개 에이전트 순차 실행
    plan       = agent_planner(transcript_text)
    clips_data = agent_extractor(transcript_text, plan)
    final      = agent_reviewer(plan, clips_data, video_title)
    
    # 결과 저장
    os.makedirs("./analyzed", exist_ok=True)
    output_path = f"./analyzed/{video_title}_agents.json"
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump({
            "plan": plan,
            "raw_clips": clips_data,
            "final": final
        }, f, ensure_ascii=False, indent=2)
    
    print(f"\n✅ 완료! 결과 저장: {output_path}")
    
    # 최종 승인 클립 요약 출력
    print(f"\n{'='*50}")
    print("📋 최종 승인 클립 요약")
    print(f"{'='*50}")
    approved_clips = [c for c in final['clips'] if c['approved']]
    for i, clip in enumerate(approved_clips, 1):
        print(f"\n[{i}] {clip['start']} ~ {clip['end']}")
        print(f"    대사: {clip['text']}")
        print(f"    우선순위: {clip['tags']['우선순위']}")
        print(f"    제목 후보: {clip['title_suggestion']}")
    
    return final


# ─────────────────────────────────────────
# 실행
# ─────────────────────────────────────────
if __name__ == "__main__":
    RESULT_DIR = "./results"
    
    txt_files = sorted([
        f for f in os.listdir(RESULT_DIR) 
        if f.endswith(".txt")
    ])
    
    if not txt_files:
        raise FileNotFoundError("results/ 폴더에 txt 파일이 없습니다.")
    
    # 파트별로 묶기
    video_titles = list(dict.fromkeys([
        f.split("_transcript_part")[0] 
        for f in txt_files
    ]))
    
    for video_title in video_titles:
        part_files = sorted([
            f for f in txt_files 
            if f.startswith(video_title)
        ])
        
        # 모든 파트 합치기
        full_transcript = ""
        for pf in part_files:
            with open(os.path.join(RESULT_DIR, pf), "r", encoding="utf-8") as f:
                full_transcript += f.read() + "\n"
        
        # 에이전트 실행
        run_agents(full_transcript, video_title)
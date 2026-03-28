# =============================================
# WISSLIST - 스크립트 자동 생성
# 실행: python generate_script.py 버터링
#       python generate_script.py 버터링 --hook 반전
#
# WEB_PROMPT.txt의 시스템 프롬프트를 그대로 사용
# → Claude.ai 웹 채팅과 동일한 결과
# → JSON 자동 저장 (제품명.json + today_script.json)
# =============================================

import sys
import json
import re
import argparse
import requests
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from config import BASE_DIR, ANTHROPIC_API_KEY

BASE        = Path(BASE_DIR)
SCRIPT_DIR  = BASE / "scripts_json"
PROMPT_FILE = BASE / "scripts" / "WEB_PROMPT.txt"


def load_system_prompt() -> str:
    """WEB_PROMPT.txt에서 시스템 프롬프트 로드"""
    if not PROMPT_FILE.exists():
        raise FileNotFoundError(
            f"WEB_PROMPT.txt를 찾을 수 없습니다: {PROMPT_FILE}\n"
            f"D:\\WISSLIST\\scripts\\WEB_PROMPT.txt 파일이 있는지 확인하세요."
        )
    content = PROMPT_FILE.read_text(encoding="utf-8")

    # 헤더/푸터 구분선 제거 (프롬프트 본문만 추출)
    lines = content.split("\n")
    body_lines = []
    in_body = False
    for line in lines:
        if line.startswith("━") and not in_body:
            in_body = True
            continue
        if line.startswith("━") and in_body:
            in_body = False
            continue
        if in_body:
            body_lines.append(line)

    prompt = "\n".join(body_lines).strip()
    if not prompt:
        # 구분선 없으면 전체 사용
        prompt = content.strip()
    return prompt


def call_api(product_name: str, extra: str = "") -> dict:
    system_prompt = load_system_prompt()

    user_msg = f"제품명: {product_name}"
    if extra:
        user_msg += f"\n{extra}"
    user_msg += "\n\nJSON만 출력해."

    headers = {
        "x-api-key": ANTHROPIC_API_KEY,
        "anthropic-version": "2023-06-01",
        "content-type": "application/json",
    }
    body = {
        "model": "claude-sonnet-4-20250514",
        "max_tokens": 4096,
        "system": system_prompt,
        "messages": [{"role": "user", "content": user_msg}],
    }

    print(f"  API 호출 중... (제품명: {product_name})")
    resp = requests.post(
        "https://api.anthropic.com/v1/messages",
        headers=headers, json=body, timeout=90
    )

    if resp.status_code != 200:
        raise RuntimeError(
            f"API 오류 {resp.status_code}: {resp.text[:400]}\n"
            f"ANTHROPIC_API_KEY가 config.py에 올바르게 입력되어 있는지 확인하세요."
        )

    content = resp.json()["content"][0]["text"].strip()

    # JSON 파싱 (```json ... ``` 블록 처리)
    json_match = re.search(r"```(?:json)?\s*(\{.*?\})\s*```", content, re.DOTALL)
    if json_match:
        content = json_match.group(1)
    elif not content.startswith("{"):
        start = content.find("{")
        end   = content.rfind("}") + 1
        if start != -1 and end > start:
            content = content[start:end]

    return json.loads(content)


def generate(product_name: str, extra: str = "") -> dict:
    SCRIPT_DIR.mkdir(exist_ok=True)

    print(f"\n🎬 스크립트 자동 생성")
    print(f"   제품명: {product_name}")
    print(f"   WEB_PROMPT.txt 로드 완료")

    script = call_api(product_name, extra)

    # product_name 필드 보장
    if "product_name" not in script:
        script["product_name"] = product_name

    # 제품명.json 저장
    safe_name = "".join(c for c in product_name
                        if c.isalnum() or c in " _-").strip()
    product_json = SCRIPT_DIR / f"{safe_name}.json"
    with open(product_json, "w", encoding="utf-8") as f:
        json.dump(script, f, ensure_ascii=False, indent=2)

    # today_script.json 덮어쓰기
    today_json = SCRIPT_DIR / "today_script.json"
    with open(today_json, "w", encoding="utf-8") as f:
        json.dump(script, f, ensure_ascii=False, indent=2)

    seg_count = len(script.get("segments", []))
    print(f"\n✅ 생성 완료!")
    print(f"   제목: {script.get('title', '')}")
    print(f"   훅 유형: {script.get('hook_type', '')}")
    print(f"   segments: {seg_count}개")
    print(f"\n   저장됨: {product_json}")
    print(f"   저장됨: {today_json}")
    print(f"\n다음: python D:\\WISSLIST\\scripts\\assemble_video.py")

    return script


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="WISSLIST 스크립트 자동 생성")
    parser.add_argument("product", nargs="?", help="제품명 (예: 버터링)")
    parser.add_argument("--hook", default="", help="훅 유형 힌트 (예: 반전)")
    parser.add_argument("--context", default="", help="추가 컨텍스트 (예: '야식 시간, 자취방')")
    args = parser.parse_args()

    if not BASE.exists():
        print("❌ D드라이브(USB) 연결 확인")
        sys.exit(1)

    if not args.product:
        print("\n🛒 WISSLIST 스크립트 자동 생성기")
        print("   (WEB_PROMPT.txt의 프롬프트를 그대로 사용)")
        args.product = input("\n제품명 입력 (예: 버터링): ").strip()
        if not args.product:
            sys.exit(1)

    extra_parts = []
    if args.hook:
        extra_parts.append(f"최근 사용 훅: {args.hook}")
    if args.context:
        extra_parts.append(f"이번 설정: {args.context}")

    generate(args.product, "\n".join(extra_parts))

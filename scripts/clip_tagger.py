# =============================================
# WISSLIST - CLIP 보완 태깅 (확장 버전)
# 실행: python clip_tagger.py
#       python clip_tagger.py 100
#
# CLIP 동작 설명:
#   - 파일을 이동하지 않습니다 (원래 위치 유지)
#   - library.json 의 all_tags 에만 태그를 추가합니다
#   - clip_verified=True 로 변경해서 재처리 방지
# =============================================

import sys, torch
from pathlib import Path
from PIL import Image
from transformers import CLIPProcessor, CLIPModel

sys.path.insert(0, str(Path(__file__).parent))
from library import load_library, save_library
from tag_map import TAG_SCHEMA

torch.set_num_threads(8)

# CLIP용 영문 설명 매핑 (tag_map의 TAG_SCHEMA와 동일 키 사용)
ENG = {
    # scene_type
    "실내생활":"indoor home daily life",
    "주방조리":"kitchen cooking food preparation",
    "거실풍경":"living room cozy home interior",
    "침실인테리어":"bedroom interior cozy",
    "욕실뷰티":"bathroom skincare beauty routine",
    "홈오피스":"home office desk working",
    "카페분위기":"cafe coffee shop ambiance",
    "음식클로즈업":"food close up delicious dish",
    "음식준비중":"food preparation cooking process",
    "음식완성샷":"completed dish food presentation",
    "디저트":"dessert cake pastry sweet",
    "배달음식":"food delivery takeout bag",
    "편의점음식":"convenience store snack food",
    "라면조리":"instant noodles ramen cooking",
    "제품단독":"product shot white background",
    "제품언박싱":"product unboxing opening box",
    "제품사용중":"person using product demonstration",
    "제품비교":"product comparison side by side",
    "가전제품":"home appliance electronics device",
    "소형가전":"small kitchen appliance gadget",
    "뷰티제품":"beauty skincare cosmetics product",
    "식품패키지":"food packaging label product",
    "인물감정":"person facial expression emotion",
    "인물리액션":"person reaction surprise expression",
    "인물일상":"person everyday daily life",
    "혼자식사":"person eating alone meal",
    "혼자쇼핑":"person shopping alone",
    "야외활동":"outdoor nature activity park",
    "마트쇼핑":"supermarket shopping cart grocery",
    "온라인쇼핑화면":"smartphone online shopping app screen",
    "택배도착":"package delivery box arrival",
    "텍스트배경":"minimal plain background text overlay",
    "숫자가격표":"price tag number label",
    "비교대조":"comparison contrast two options",
    "비포애프터":"before after transformation result",
    "영수증클로즈업":"receipt price total close up",
    "쿠팡앱화면":"shopping app mobile screen cart",
    # mood
    "따뜻한":"warm cozy inviting comfortable",
    "신나는":"exciting energetic fun",
    "설레는":"excited anticipation thrilling",
    "만족스러운":"satisfied pleased happy result",
    "뿌듯한":"proud accomplished achievement",
    "공감가는":"relatable realistic everyday",
    "현실적인":"realistic ordinary mundane",
    "피곤한":"tired exhausted sleepy",
    "귀찮은":"lazy annoyed bothered",
    "허탈한":"disappointed defeated empty",
    "유머러스한":"funny humorous playful",
    "황당한":"absurd ridiculous bizarre",
    "어이없는":"disbelief exasperated",
    "웃긴":"funny laughing comic",
    "신뢰감있는":"trustworthy reliable professional",
    "전문적인":"professional expert formal",
    "깔끔한":"clean neat organized minimal",
    "세련된":"stylish elegant sophisticated",
    "아늑한":"cozy homey soft gentle",
    "역동적인":"dynamic action motion energetic",
    # color_tone
    "화이트톤":"white bright light clean",
    "따뜻한계열":"warm orange yellow brown tones",
    "차가운계열":"cool blue gray silver",
    "어두운계열":"dark moody low light",
    "자연초록":"natural green nature plants",
    "음식풍부한색감":"rich colorful food vibrant",
    "파스텔톤":"pastel soft pink lavender",
    "비비드컬러":"vivid bright saturated color",
    "모노크롬":"monochrome black white gray",
    "골드브라운":"gold brown warm metallic",
    # usability
    "훅배경":"abstract background blur bokeh",
    "제품등장":"product reveal showcase display",
    "감정표현":"emotion expression reaction face",
    "조리과정":"cooking steps process making",
    "비포애프터":"before after change",
    "가격강조":"price highlight discount sale",
    "클로징":"ending conclusion final shot",
    "자막배경":"plain background subtitle text",
    "언박싱":"unboxing opening reveal package",
    "사용후기":"product review using experience",
    "불편함표현":"discomfort problem inconvenience",
    "해결완료":"problem solved satisfied result",
}


def load_model():
    print("CLIP 모델 로딩 중... (최초 실행 시 약 600MB 다운로드)")
    m = CLIPModel.from_pretrained("openai/clip-vit-base-patch32")
    p = CLIPProcessor.from_pretrained("openai/clip-vit-base-patch32")
    m.eval()
    print("로딩 완료")
    return m, p


def tag_one(path, model, proc, top_k=2):
    try:
        img = Image.open(path).convert("RGB")
    except Exception as e:
        print(f"    이미지 열기 실패: {e}")
        return []

    result = []
    with torch.no_grad():
        for cat, tags in TAG_SCHEMA.items():
            valid_tags = [t for t in tags if t in ENG]
            if not valid_tags:
                continue
            texts  = [ENG[t] for t in valid_tags]
            inputs = proc(text=texts, images=img,
                          return_tensors="pt", padding=True)
            probs  = model(**inputs).logits_per_image.softmax(dim=1)[0]
            tops   = probs.topk(min(top_k, len(valid_tags))).indices.tolist()
            result += [valid_tags[i] for i in tops]
    return list(set(result))


def run(max_n=50):
    library = load_library()
    targets = [
        item for item in library
        if not item.get("clip_verified", False)
        and Path(item["file"]).exists()
        and not item["file"].lower().endswith(".gif")
    ]

    if not targets:
        print("
 CLIP 검증할 항목 없음 (모두 완료)")
        print(" import_custom.py 로 이미지를 먼저 등록하세요.")
        return

    print(f"
 CLIP 보완 태깅: {len(targets)}개 중 최대 {max_n}개")
    print(" 파일을 이동하지 않고 태그만 library.json에 추가합니다.
")

    model, proc = load_model()

    for i, item in enumerate(targets[:max_n]):
        fname = Path(item["file"]).name
        print(f"  [{i+1}/{min(len(targets),max_n)}] {fname}")

        new_tags = tag_one(item["file"], model, proc)
        if new_tags:
            before = set(item["all_tags"])
            item["all_tags"] = list(set(item["all_tags"]) | set(new_tags))
            added = set(item["all_tags"]) - before
            if added:
                print(f"    추가된 태그: {list(added)}")
        item["clip_verified"] = True

        if (i + 1) % 10 == 0:
            save_library(library)
            print(f"    중간 저장 ({i+1}개)")

    save_library(library)
    print(f"
 완료: {min(len(targets), max_n)}개 처리")
    print(f" 전체 라이브러리: {len(library)}개")


if __name__ == "__main__":
    max_n = int(sys.argv[1]) if len(sys.argv) > 1 else 50
    run(max_n)

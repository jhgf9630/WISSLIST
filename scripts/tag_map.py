# =============================================
# WISSLIST - 태그 매핑 (음식 특화 확장판)
# =============================================

TAG_SCHEMA = {
    "scene_type": [
        "실내생활","주방조리","거실풍경","침실인테리어","욕실뷰티",
        "홈오피스","카페분위기",
        "음식클로즈업","음식준비중","음식완성샷","디저트",
        "배달음식","편의점음식","라면조리",
        "제품단독","제품언박싱","제품사용중","제품비교",
        "가전제품","소형가전","뷰티제품","식품패키지",
        "인물감정","인물리액션","인물일상","혼자식사","혼자쇼핑",
        "야외활동","마트쇼핑","온라인쇼핑화면","택배도착",
        "텍스트배경","숫자가격표","비교대조","비포애프터",
        "영수증클로즈업","쿠팡앱화면",
    ],
    "mood": [
        "따뜻한","신나는","설레는","만족스러운","뿌듯한",
        "공감가는","현실적인","피곤한","귀찮은","허탈한",
        "유머러스한","황당한","어이없는","웃긴",
        "신뢰감있는","전문적인","깔끔한","세련된",
        "아늑한","역동적인",
    ],
    "color_tone": [
        "화이트톤","따뜻한계열","차가운계열","어두운계열",
        "자연초록","음식풍부한색감","파스텔톤","비비드컬러",
        "모노크롬","골드브라운",
    ],
    "usability": [
        "훅배경","제품등장","감정표현","조리과정",
        "비포애프터","가격강조","클로징","자막배경",
        "언박싱","사용후기","불편함표현","해결완료",
    ],
    "subject": [
        "라면","치킨","피자","햄버거","삼겹살","떡볶이",
        "냉동식품","간편식","컵라면","캔음식",
        "에어프라이어","전자레인지","믹서기","커피머신",
        "청소기","가습기","선풍기","히터",
        "스킨케어","마스크팩","샴푸","세제","방향제",
        "택배박스","쿠팡박스","장바구니","할인쿠폰",
        "놀란표정","만족표정","실망표정","기쁜표정",
        "팝콘먹는사람",
        "깔끔한흰배경","원목테이블","대리석배경",
    ],
}

QUERY_TAG_MAP = {
    # ── 음식 특화 (핵심) ──────────────────────────────────────────
    "kitchen cooking":          ["주방조리","따뜻한","조리과정","음식준비중"],
    "food preparation":         ["주방조리","조리과정","역동적인","음식준비중"],
    "kitchen appliance":        ["가전제품","소형가전","제품등장","화이트톤"],
    "air fryer cooking":        ["에어프라이어","소형가전","조리과정","사용후기"],
    "microwave food":           ["전자레인지","간편식","현실적인","조리과정"],
    "instant noodles":          ["라면","컵라면","라면조리","공감가는"],
    "ramen noodle soup":        ["라면","라면조리","따뜻한","음식클로즈업"],
    "korean food":              ["음식클로즈업","음식풍부한색감","따뜻한","음식완성샷"],
    "korean street food":       ["음식클로즈업","음식풍부한색감","신나는","혼자식사"],
    "delicious meal":           ["음식클로즈업","음식완성샷","만족스러운","클로징"],
    "food close up":            ["음식클로즈업","음식풍부한색감","제품등장"],
    "food photography":         ["음식클로즈업","음식완성샷","음식풍부한색감","화이트톤"],
    "appetizing food":          ["음식클로즈업","음식풍부한색감","만족스러운","따뜻한"],
    "delivery food":            ["배달음식","택배도착","설레는","언박싱"],
    "food delivery unboxing":   ["배달음식","언박싱","설레는","음식클로즈업"],
    "convenience store":        ["편의점음식","간편식","현실적인","혼자식사"],
    "frozen food":              ["냉동식품","간편식","가전제품","공감가는"],
    "chicken":                  ["치킨","음식클로즈업","신나는","음식완성샷"],
    "fried chicken":            ["치킨","음식클로즈업","신나는","음식풍부한색감"],
    "dessert sweet":            ["디저트","파스텔톤","따뜻한","음식클로즈업"],
    "cake bakery":              ["디저트","파스텔톤","카페분위기","음식클로즈업"],
    "coffee cafe":              ["카페분위기","따뜻한","세련된","음식클로즈업"],
    "cooking process":          ["주방조리","조리과정","역동적인","음식준비중"],
    "steam hot food":           ["음식클로즈업","따뜻한계열","만족스러운","음식완성샷"],
    "melting cheese":           ["음식클로즈업","음식풍부한색감","신나는","만족스러운"],

    # ── 감정/리액션 (GIF 매칭 최적화) ────────────────────────────
    "person expression":        ["인물감정","감정표현","공감가는","인물리액션"],
    "happy surprised":          ["놀란표정","유머러스한","황당한","인물리액션"],
    "satisfied smile":          ["만족표정","만족스러운","뿌듯한","클로징"],
    "disappointed reaction":    ["실망표정","허탈한","어이없는","불편함표현"],
    "person eating popcorn":    ["팝콘먹는사람","유머러스한","인물리액션","훅배경"],
    "shocked reaction":         ["놀란표정","황당한","어이없는","인물리액션"],
    "thumbs up":                ["기쁜표정","뿌듯한","해결완료","신뢰감있는"],
    "eating reaction":          ["인물리액션","유머러스한","혼자식사","감정표현"],
    "food reaction":            ["인물리액션","유머러스한","음식클로즈업","감정표현"],
    "yummy delicious face":     ["만족표정","유머러스한","혼자식사","공감가는"],

    # ── 라이프스타일 ──────────────────────────────────────────────
    "daily life":               ["실내생활","현실적인","공감가는","인물일상"],
    "home living":              ["거실풍경","아늑한","따뜻한","실내생활"],
    "cozy interior":            ["침실인테리어","아늑한","파스텔톤","자막배경"],
    "working from home":        ["홈오피스","깔끔한","현실적인","신뢰감있는"],
    "morning routine":          ["실내생활","피곤한","공감가는","인물일상"],
    "late night snack":         ["음식준비중","어두운계열","공감가는","현실적인"],
    "camping outdoor":          ["야외활동","역동적인","자연초록","설레는"],
    "nature activity":          ["야외활동","자연초록","신나는","역동적인"],
    "park walk":                ["야외활동","따뜻한","자연초록","인물일상"],

    # ── 제품/가전 ──────────────────────────────────────────────────
    "gadget electronics":       ["가전제품","제품단독","세련된","차가운계열"],
    "smartphone":               ["가전제품","온라인쇼핑화면","세련된","제품사용중"],
    "home appliance":           ["소형가전","가전제품","신뢰감있는","화이트톤"],
    "robot vacuum":             ["청소기","소형가전","사용후기","해결완료"],
    "skincare routine":         ["욕실뷰티","뷰티제품","스킨케어","세련된"],
    "exercise fitness":         ["야외활동","역동적인","신나는","자연초록"],
    "wellness":                 ["실내생활","따뜻한","신뢰감있는","만족스러운"],
    "mask pack":                ["마스크팩","욕실뷰티","유머러스한","공감가는"],
    "baby products":            ["제품단독","따뜻한","공감가는","파스텔톤"],
    "children playing":         ["실내생활","신나는","유머러스한","따뜻한"],
    "family":                   ["실내생활","따뜻한","공감가는","거실풍경"],

    # ── 배경 ─────────────────────────────────────────────────────
    "minimal background":       ["텍스트배경","깔끔한","자막배경","화이트톤"],
    "white background":         ["텍스트배경","깔끔한흰배경","화이트톤","자막배경"],
    "clean simple":             ["텍스트배경","깔끔한","모노크롬","자막배경"],
    "marble background":        ["대리석배경","세련된","차가운계열","자막배경"],
    "wood table":               ["원목테이블","따뜻한계열","아늑한","자막배경"],

    # ── 쇼핑/가격 ─────────────────────────────────────────────────
    "shopping purchase":        ["마트쇼핑","온라인쇼핑화면","설레는"],
    "price tag":                ["숫자가격표","가격강조","비교대조","영수증클로즈업"],
    "discount sale":            ["할인쿠폰","가격강조","신나는","숫자가격표"],
    "unboxing package":         ["택배박스","언박싱","설레는","제품등장"],
    "coupang delivery":         ["쿠팡박스","택배박스","언박싱","설레는"],
    "online shopping":          ["쿠팡앱화면","온라인쇼핑화면","혼자쇼핑","설레는"],
    "receipt price":            ["영수증클로즈업","숫자가격표","허탈한","가격강조"],

    # ── GIF 전용 ─────────────────────────────────────────────────
    "delicious food reaction":  ["인물리액션","유머러스한","음식클로즈업","감정표현"],
    "surprised reaction":       ["놀란표정","황당한","인물리액션","훅배경"],
    "happy excited":            ["기쁜표정","신나는","인물리액션","설레는"],
    "amazing wow":              ["놀란표정","황당한","인물리액션","역동적인"],
    "thumbs up reaction":       ["기쁜표정","만족스러운","해결완료","클로징"],
    "cooking food gif":         ["라면조리","주방조리","유머러스한","조리과정"],
    "eating delicious":         ["음식클로즈업","만족스러운","유머러스한","혼자식사"],
    "food satisfaction":        ["만족표정","음식완성샷","만족스러운","클로징"],
    "shopping excited":         ["쿠팡박스","설레는","유머러스한","언박싱"],
    "unboxing package gif":     ["택배박스","설레는","역동적인","언박싱"],
    "money saving gif":         ["할인쿠폰","가격강조","신나는","유머러스한"],
    "frustrated annoyed":       ["실망표정","피곤한","불편함표현","현실적인"],
    "mind blown":               ["놀란표정","황당한","어이없는","인물리액션"],
    "person eating noodles":    ["혼자식사","유머러스한","라면","감정표현"],
    "woman eating":             ["혼자식사","만족스러운","음식클로즈업","공감가는"],
}

# ─── 카테고리별 수집 쿼리 (음식 특화) ────────────────────────────
CATEGORY_QUERIES = {
    "kitchen":       [
        "kitchen cooking", "food preparation", "kitchen appliance",
        "air fryer cooking", "microwave food", "instant noodles",
        "ramen noodle soup", "cooking process",
    ],
    "food":          [
        "korean food", "delicious meal", "food close up",
        "delivery food", "chicken", "fried chicken",
        "frozen food", "dessert sweet", "cake bakery",
        "food photography", "appetizing food", "steam hot food",
        "melting cheese", "coffee cafe", "korean street food",
    ],
    "lifestyle":     [
        "daily life", "home living", "cozy interior",
        "working from home", "morning routine", "late night snack",
    ],
    "outdoor":       ["camping outdoor", "nature activity", "park walk"],
    "tech_gadgets":  ["gadget electronics", "smartphone", "home appliance", "robot vacuum"],
    "health_beauty": ["skincare routine", "exercise fitness", "wellness", "mask pack"],
    "baby_kids":     ["baby products", "children playing", "family"],
    "text_bg":       [
        "minimal background", "white background", "marble background",
        "wood table", "clean simple",
    ],
    "emotion":       [
        "person expression", "happy surprised", "satisfied smile",
        "disappointed reaction", "shocked reaction", "thumbs up",
        "person eating popcorn", "eating reaction", "yummy delicious face",
    ],
    "money_price":   [
        "shopping purchase", "price tag", "discount sale",
        "unboxing package", "coupang delivery", "online shopping",
        "receipt price",
    ],
}

GIF_CATEGORY_QUERIES = {
    "reaction_gif": [
        "delicious food reaction", "surprised reaction", "happy excited",
        "amazing wow", "thumbs up reaction", "frustrated annoyed",
        "mind blown", "person eating noodles", "woman eating",
        "eating reaction", "food reaction",
    ],
    "food_gif": [
        "cooking food gif", "eating delicious", "food satisfaction",
        "ramen cooking", "cheese pull",
    ],
    "shopping_gif": [
        "shopping excited", "unboxing package gif", "money saving gif",
    ],
}

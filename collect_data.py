import os
import re
import sys
import html
import json
import time
import requests
import pycountry
import xml.etree.ElementTree as ET
from html.parser import HTMLParser
from dotenv import load_dotenv

sys.stdout.reconfigure(encoding='utf-8')

load_dotenv(dotenv_path=os.path.join(os.path.dirname(__file__), ".env"))
SERVICE_KEY = os.getenv("PUBLIC_DATA_SERVICE_KEY")
GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY")

GEMINI_MODEL = "gemini-flash-lite-latest"

DATA_DIR = os.path.join(os.path.dirname(__file__), "public", "data")
COUNTRIES_DIR = os.path.join(DATA_DIR, "countries")
IMAGES_DIR = os.path.join(os.path.dirname(__file__), "public", "images")

# ISO 3166-1 alpha-3 -> approximate country centroid (lat, lng)
# Source: https://github.com/mledoze/countries (public domain country reference data)
# XKX (Kosovo) is not an official ISO 3166-1 code; manually added (Pristina coords).
COUNTRY_COORDS = {
    "AFG": (33, 65), "AGO": (-12.5, 18.5), "ALB": (41, 20), "AND": (42.5, 1.5),
    "ARE": (24, 54), "ARG": (-34, -64), "ARM": (40, 45), "ATG": (17.05, -61.8),
    "AUS": (-27, 133), "AUT": (47.33333333, 13.33333333), "AZE": (40.5, 47.5),
    "BDI": (-3.5, 30), "BEL": (50.83333333, 4), "BEN": (9.5, 2.25), "BFA": (13, -2),
    "BGD": (24, 90), "BGR": (43, 25), "BHR": (26, 50.55), "BHS": (24.25, -76),
    "BIH": (44, 18), "BLR": (53, 28), "BLZ": (17.25, -88.75), "BOL": (-17, -65),
    "BRA": (-10, -55), "BRB": (13.16666666, -59.53333333), "BRN": (4.5, 114.66666666),
    "BTN": (27.5, 90.5), "BWA": (-22, 24), "CAF": (7, 21), "CAN": (60, -95),
    "CHE": (47, 8), "CHL": (-30, -71), "CHN": (35, 105), "CIV": (8, -5),
    "CMR": (6, 12), "COD": (0, 25), "COG": (-1, 15), "COK": (-21.23333333, -159.76666666),
    "COL": (4, -72), "COM": (-12.16666666, 44.25), "CPV": (16, -24), "CRI": (10, -84),
    "CUB": (21.5, -80), "CYP": (35, 33), "CZE": (49.75, 15.5), "DEU": (51, 9),
    "DJI": (11.5, 43), "DMA": (15.41666666, -61.33333333), "DNK": (56, 10),
    "DOM": (19, -70.66666666), "DZA": (28, 3), "ECU": (-2, -77.5), "EGY": (27, 30),
    "ERI": (15, 39), "ESP": (40, -4), "EST": (59, 26), "ETH": (8, 38),
    "FIN": (64, 26), "FJI": (-18, 175), "FRA": (46, 2), "FSM": (6.91666666, 158.25),
    "GAB": (-1, 11.75), "GBR": (54, -2), "GEO": (42, 43.5), "GHA": (8, -2),
    "GIN": (11, -10), "GMB": (13.46666666, -16.56666666), "GNB": (12, -15),
    "GNQ": (2, 10), "GRC": (39, 22), "GRD": (12.11666666, -61.66666666),
    "GTM": (15.5, -90.25), "GUY": (5, -59), "HKG": (22.267, 114.188), "HND": (15, -86.5),
    "HRV": (45.16666666, 15.5), "HTI": (19, -72.41666666), "HUN": (47, 20),
    "IDN": (-5, 120), "IND": (20, 77), "IRL": (53, -8), "IRN": (32, 53),
    "IRQ": (33, 44), "ISL": (65, -18), "ISR": (31.47, 35.13), "ITA": (42.83333333, 12.83333333),
    "JAM": (18.25, -77.5), "JOR": (31, 36), "JPN": (36, 138), "KAZ": (48, 68),
    "KEN": (1, 38), "KGZ": (41, 75), "KHM": (13, 105), "KIR": (1.41666666, 173),
    "KNA": (17.33333333, -62.75), "KWT": (29.5, 45.75), "LAO": (18, 105),
    "LBN": (33.83333333, 35.83333333), "LBR": (6.5, -9.5), "LBY": (25, 17),
    "LCA": (13.88333333, -60.96666666), "LIE": (47.26666666, 9.53333333),
    "LKA": (7, 81), "LSO": (-29.5, 28.5), "LTU": (56, 24), "LUX": (49.75, 6.16666666),
    "LVA": (57, 25), "MAR": (32, -5), "MCO": (43.73333333, 7.4), "MDA": (47, 29),
    "MDG": (-20, 47), "MDV": (3.25, 73), "MEX": (23, -102), "MHL": (9, 168),
    "MKD": (41.83333333, 22), "MLI": (17, -4), "MLT": (35.83333333, 14.58333333),
    "MMR": (22, 98), "MNE": (42.5, 19.3), "MNG": (46, 105), "MOZ": (-18.25, 35),
    "MRT": (20, -12), "MUS": (-20.28333333, 57.55), "MWI": (-13.5, 34), "MYS": (2.5, 112.5),
    "NAM": (-22, 17), "NER": (16, 8), "NGA": (10, 8), "NIC": (13, -85),
    "NIU": (-19.03333333, -169.86666666), "NLD": (52.5, 5.75), "NOR": (62, 10),
    "NPL": (28, 84), "NRU": (-0.53333333, 166.91666666), "NZL": (-41, 174),
    "OMN": (21, 57), "PAK": (30, 70), "PAN": (9, -80), "PER": (-10, -76),
    "PHL": (13, 122), "PLW": (7.5, 134.5), "PNG": (-6, 147), "POL": (52, 20),
    "PRT": (39.5, -8), "PRY": (-23, -58), "PSE": (31.9, 35.2), "QAT": (25.5, 51.25),
    "ROU": (46, 25), "RUS": (60, 100), "RWA": (-2, 30), "SAU": (25, 45),
    "SDN": (15, 30), "SEN": (14, -14), "SGP": (1.36666666, 103.8), "SLB": (-8, 159),
    "SLE": (8.5, -11.5), "SLV": (13.83333333, -88.91666666), "SMR": (43.76666666, 12.41666666),
    "SOM": (10, 49), "SRB": (44, 21), "SSD": (7, 30), "STP": (1, 7),
    "SUR": (4, -56), "SVK": (48.66666666, 19.5), "SVN": (46.11666666, 14.81666666),
    "SWE": (62, 15), "SWZ": (-26.5, 31.5), "SYC": (-4.58333333, 55.66666666),
    "SYR": (35, 38), "TCD": (15, 19), "TGO": (8, 1.16666666), "THA": (15, 100),
    "TJK": (39, 71), "TKM": (40, 60), "TLS": (-8.83333333, 125.91666666),
    "TON": (-20, -175), "TTO": (11, -61), "TUN": (34, 9), "TUR": (39, 35),
    "TUV": (-8, 178), "TWN": (23.5, 121), "TZA": (-6, 35), "UGA": (1, 32),
    "UKR": (49, 32), "URY": (-33, -56), "USA": (38, -97), "UZB": (41, 64),
    "VCT": (13.25, -61.2), "VEN": (8, -66), "VNM": (16.16666666, 107.83333333),
    "VUT": (-16, 167), "WSM": (-13.58333333, -172.33333333), "XKX": (42.6026, 20.903),
    "YEM": (15, 48), "ZAF": (-29, 24), "ZMB": (-15, 30), "ZWE": (-20, 30),
}

# Travel warning level -> (background color, text color), per CultureZero_기획서.md section 5
# 여행유의 added as a 5th tier (navy) since the official MOFA system has 4 numbered levels,
# but the 기획서 color table only specified 3 numbered levels + none.
LEVEL_COLORS = {
    "없음": ("#E8F5E0", "#3B7D2E"),
    "여행유의": ("#E0ECFA", "#2E5B9D"),
    "여행자제": ("#FFF3E0", "#C77700"),
    "철수권고": ("#FFE0CC", "#D45500"),
    "여행금지": ("#FCE0E0", "#C0392B"),
}
LEVEL_RANK = {"없음": 0, "여행유의": 1, "여행자제": 2, "철수권고": 3, "여행금지": 4}

NOTICE_FALLBACK_URL = "https://www.0404.go.kr/ntnSafetyInfo/list"

# Natural Earth 1:50m country boundaries (public domain). Used for the choropleth map.
WORLD_BORDERS_URL = "https://raw.githubusercontent.com/nvkelso/natural-earth-vector/master/geojson/ne_50m_admin_0_countries.geojson"


def fetch_world_borders(iso3_set):
    """Download + slim the world country-borders GeoJSON, keyed by iso_code.
    Cached on disk since country borders don't change between runs."""
    dest = os.path.join(DATA_DIR, "world_borders.geojson")
    if os.path.exists(dest):
        print("world_borders.geojson already cached, skipping download.")
        return

    print("Fetching world country borders (Natural Earth 50m)...")
    res = requests.get(WORLD_BORDERS_URL, timeout=60)
    res.raise_for_status()
    raw = res.json()

    # Natural Earth은 미승인/분쟁 지역을 별도 feature로 표기해 우리 197개국 마스터에
    # 없는 ISO코드가 붙는다. 그대로 두면 지도에 색칠 안 된 구멍(서사하라, 소말릴란드)이
    # 생기므로, 실효 지배/UN 승인 기준 모국(母國)으로 흡수시켜 함께 칠한다.
    DISPUTED_TERRITORY_REMAP = {
        "ESH": "MAR",  # 서사하라 → 모로코 (모리타니아 옆 색칠 누락 구간)
        "SOL": "SOM",  # 소말릴란드 → 소말리아 (에티오피아 옆 색칠 누락 구간)
    }

    def resolve_iso3(props):
        iso = props.get("ISO_A3")
        if not iso or iso == "-99":
            iso = props.get("ADM0_A3")
        return DISPUTED_TERRITORY_REMAP.get(iso, iso)

    slim_features = []
    for feature in raw["features"]:
        iso3 = resolve_iso3(feature["properties"])
        # 위 리매핑으로 한 국가에 폴리곤이 2개(본토+분쟁지역) 붙을 수 있으므로
        # iso3 기준 중복 제거는 하지 않는다(모두 같은 색으로 칠해져야 함).
        if iso3 in iso3_set:
            slim_features.append({
                "type": "Feature",
                "properties": {"iso_code": iso3},
                "geometry": feature["geometry"],
            })

    with open(dest, "w", encoding="utf-8") as f:
        json.dump({"type": "FeatureCollection", "features": slim_features}, f, separators=(",", ":"))
    saved_iso = {f["properties"]["iso_code"] for f in slim_features}
    print(f"  {len(slim_features)} borders saved for {len(saved_iso)}/{len(iso3_set)} countries (missing: {sorted(iso3_set - saved_iso)})")


def iso2_to_iso3(alpha2):
    if alpha2 == "XK":
        return "XKX"  # Kosovo: not an official ISO 3166-1 code, MOFA-specific
    c = pycountry.countries.get(alpha_2=alpha2)
    return c.alpha_3 if c else None


_SANITIZE_ALLOWED_TAGS = {"div", "p", "br", "h3", "b", "strong", "a"}


class _HTMLSanitizer(HTMLParser):
    """Rebuilds source HTML keeping only a safe tag allowlist (drops inline style/class
    cruft from the source CMS) and recovers gracefully from malformed/truncated markup
    (some API fields are cut off mid-tag for very long entries, e.g. Russia/Hungary)."""

    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.out = []

    def handle_starttag(self, tag, attrs):
        if tag == "br":
            self.out.append("<br>")
        elif tag == "a":
            href = dict(attrs).get("href", "") or ""
            self.out.append(f'<a href="{html.escape(href, quote=True)}" target="_blank" rel="noopener">')
        elif tag in _SANITIZE_ALLOWED_TAGS:
            self.out.append(f"<{tag}>")

    def handle_startendtag(self, tag, attrs):
        if tag == "br":
            self.out.append("<br>")

    def handle_endtag(self, tag):
        if tag in _SANITIZE_ALLOWED_TAGS and tag != "br":
            self.out.append(f"</{tag}>")

    def handle_data(self, data):
        self.out.append(html.escape(data))


def sanitize_html(raw_html):
    parser = _HTMLSanitizer()
    try:
        parser.feed(raw_html)
        parser.close()
    except Exception:
        pass
    return "".join(parser.out)


def api_get(url, params, return_type="xml"):
    params = dict(params)
    params["serviceKey"] = SERVICE_KEY
    res = requests.get(url, params=params, timeout=30)
    res.raise_for_status()
    if return_type == "json":
        return res.json()
    return ET.fromstring(res.content)


def fetch_travel_warnings():
    print("Fetching TravelWarningServiceV3...")
    data = api_get(
        "https://apis.data.go.kr/1262000/TravelWarningServiceV3/getTravelWarningListV3",
        {"pageNo": 1, "numOfRows": 300},
        return_type="json",
    )
    items = data["response"]["body"]["items"]["item"]
    print(f"  {len(items)} countries")

    # Each level has a "full" field (whole-country designation) and a "_partial" field
    # (designation limited to part of the country). Both share the same _note field for
    # the affected area description. A country can have a level set via either or both.
    LEVEL_FIELDS = [
        ("여행유의", "attention", "attention_partial", "attention_note"),
        ("여행자제", "control", "control_partial", "control_note"),
        ("철수권고", "limita", "limita_partial", "limita_note"),
        ("여행금지", "ban_yna", "ban_yn_partial", "ban_note"),
    ]

    countries = {}
    for it in items:
        iso3 = it["iso_code"]
        regions = []
        for level_name, full_field, partial_field, note_field in LEVEL_FIELDS:
            if it.get(full_field) or it.get(partial_field):
                regions.append({
                    "level": level_name,
                    "area": it.get(note_field) or "",
                    "partial": bool(it.get(partial_field)) and not it.get(full_field),
                })
        def rank_to_name(rank):
            return next((k for k, v in LEVEL_RANK.items() if v == rank), "없음")

        # alert_level: highest level anywhere in the country (used for text badges —
        # conservative/safety-first, matches the per-country detail page and list view).
        overall_rank = max((LEVEL_RANK.get(r["level"], 0) for r in regions), default=0)
        level_name = rank_to_name(overall_rank)

        # national_level: highest level that applies to the WHOLE country (non-partial
        # entries only). Used for the map polygon fill — using the overall highest there
        # would paint an entire country red over one small flagged border region.
        national_rank = max(
            (LEVEL_RANK.get(r["level"], 0) for r in regions if not r["partial"]), default=0
        )
        national_level_name = rank_to_name(national_rank)

        # partial_level: highest level among region-limited-only entries, if any. Used to
        # decide whether the map should flag "elevated alert in part of this country".
        partial_ranks = [LEVEL_RANK.get(r["level"], 0) for r in regions if r["partial"]]
        partial_level_name = rank_to_name(max(partial_ranks)) if partial_ranks else None

        countries[iso3] = {
            "iso_code": iso3,
            "country_kr": it["country_name"],
            "country_en": it["country_en_name"],
            "continent": it.get("continent", ""),
            "alert_level": level_name,
            "national_level": national_level_name,
            "partial_level": partial_level_name,
            "alert_regions": regions,
        }
    return countries


def fetch_flags():
    print("Fetching CountryFlagService2...")
    data = api_get(
        "http://apis.data.go.kr/1262000/CountryFlagService2/getCountryFlagList2",
        {"pageNo": 1, "numOfRows": 250, "returnType": "JSON"},
        return_type="json",
    )
    items = data["response"]["body"]["items"]["item"]
    print(f"  {len(items)} flags")

    flags = {}
    for it in items:
        alpha2 = it["country_iso_alp2"]
        if alpha2 == "EU":
            continue  # not a country
        iso3 = iso2_to_iso3(alpha2)
        if not iso3:
            continue
        flags[iso3] = {
            "download_url": it["download_url"],
            "origin_file_nm": it.get("origin_file_nm") or "",
            "alpha2": alpha2,
        }
    return flags


def fetch_contacts():
    print("Fetching LocalContactService2...")
    data = api_get(
        "http://apis.data.go.kr/1262000/LocalContactService2/getLocalContactList2",
        {"pageNo": 1, "numOfRows": 300, "returnType": "JSON"},
        return_type="json",
    )
    items = data["response"]["body"]["items"]["item"]
    print(f"  {len(items)} contacts")

    contacts = {}
    for it in items:
        iso3 = iso2_to_iso3(it["country_iso_alp2"])
        if not iso3:
            continue
        # API returns double HTML-escaped text (e.g. "&lt;div&gt;"); unescape once to get real HTML.
        raw = html.unescape(it.get("contact_remark") or "")
        contacts[iso3] = sanitize_html(raw)
    return contacts


def fetch_accidents():
    print("Fetching AccidentService...")
    root = api_get(
        "http://apis.data.go.kr/1262000/AccidentService/getAccidentList",
        {"pageNo": 1, "numOfRows": 300},
        return_type="xml",
    )
    items = root.findall(".//item")
    print(f"  {len(items)} accident entries")

    by_name = {}
    for it in items:
        name = (it.findtext("name") or "").strip()
        news = sanitize_html(it.findtext("news") or "")
        if name:
            by_name[name] = news
    return by_name


def download_flag_image(iso3, flag_info):
    os.makedirs(IMAGES_DIR, exist_ok=True)
    alpha2 = (flag_info.get("alpha2") or "").lower()
    flagcdn_url = f"https://flagcdn.com/w40/{alpha2}.png" if alpha2 else None
    ext = os.path.splitext(flag_info["origin_file_nm"])[1] or ".png"
    dest = os.path.join(IMAGES_DIR, f"{iso3}{ext}")
    rel_path = f"public/images/{iso3}{ext}"

    if os.path.exists(dest):
        if os.path.getsize(dest) >= 500:
            return rel_path
        os.remove(dest)  # 캐시된 파일이 너무 작으면(빈 이미지) 삭제 후 재시도

    try:
        res = requests.get(flag_info["download_url"], timeout=30)
        res.raise_for_status()
        with open(dest, "wb") as f:
            f.write(res.content)
        if os.path.getsize(dest) < 500:  # API가 빈/유효하지 않은 이미지 반환 (예: 대만)
            os.remove(dest)
            return flagcdn_url
        return rel_path
    except Exception as e:
        print(f"  Failed to download flag for {iso3}: {e}")
        return flagcdn_url


def load_existing_culture_ai(iso3):
    path = os.path.join(COUNTRIES_DIR, f"{iso3}.json")
    if os.path.exists(path):
        try:
            with open(path, "r", encoding="utf-8") as f:
                existing = json.load(f)
                ai = existing.get("culture_ai")
                # local_laws 필드가 없거나 None이면 재생성 필요 (business_tip에서 변경됨)
                if ai and not ai.get("local_laws"):
                    return None
                return ai
        except Exception:
            return None
    return None


def generate_culture_ai(country_kr, country_en):
    prompt = f"""당신은 해외 여행자를 위한 안전·문화 가이드 작가입니다. "{country_kr}({country_en})"에 대한 다음 정보를 JSON으로 작성하세요.

1. etiquette: 현지 문화·예절 핵심 정보 (한국어, 3~4문장)
2. local_laws: 여행자가 모르고 지나치기 쉬운 현지 법률·경범죄·주의사항 (한국어, 2~3문장). 예: 특이한 금지 행위, 음주·복장 규정, 무심코 저지르기 쉬운 위반, 각국 특유의 처벌 등.
3. phrases: 여행자에게 유용한 현지어 표현 5개 (각각 "한국어 뜻 - 현지어 발음(현지 문자)" 형식의 문자열 배열)

반드시 아래 JSON 형식으로만 응답하세요. 마크다운 코드블록이나 다른 설명 없이 순수 JSON만 출력하세요.
{{"etiquette": "...", "local_laws": "...", "phrases": ["...", "...", "...", "...", "..."]}}"""

    url = f"https://generativelanguage.googleapis.com/v1beta/models/{GEMINI_MODEL}:generateContent?key={GOOGLE_API_KEY}"
    payload = {
        "contents": [{"parts": [{"text": prompt}]}],
        "generationConfig": {"responseMimeType": "application/json"},
    }

    for attempt in range(3):
        try:
            res = requests.post(url, json=payload, timeout=30)
            if res.status_code == 200:
                text = res.json()["candidates"][0]["content"]["parts"][0]["text"].strip()
                return json.loads(text)
            elif res.status_code in (429, 500, 502, 503, 504):
                wait_sec = (attempt + 1) * 15
                print(f"  Gemini transient error ({res.status_code}) for {country_kr}, retrying in {wait_sec}s...")
                time.sleep(wait_sec)
            else:
                print(f"  Gemini API error {res.status_code} for {country_kr}: {res.text[:200]}")
                break
        except Exception as e:
            print(f"  Gemini API exception (attempt {attempt + 1}) for {country_kr}: {e}")
            time.sleep(5)
    return None


def main():
    if not SERVICE_KEY:
        print("PUBLIC_DATA_SERVICE_KEY is not set in .env")
        return
    if not GOOGLE_API_KEY:
        print("GOOGLE_API_KEY is not set in .env — culture_ai generation will be skipped.")

    os.makedirs(COUNTRIES_DIR, exist_ok=True)

    warnings = fetch_travel_warnings()
    flags = fetch_flags()
    contacts = fetch_contacts()
    fetch_world_borders(set(warnings.keys()))
    accidents = fetch_accidents()

    countries_index = []

    for idx, (iso3, country) in enumerate(sorted(warnings.items())):
        print(f"[{idx + 1}/{len(warnings)}] {country['country_kr']} ({iso3})")

        flag_info = flags.get(iso3)
        flag_image = download_flag_image(iso3, flag_info) if flag_info else None

        lat, lng = COUNTRY_COORDS.get(iso3, (0, 0))

        accident_html = accidents.get(country["country_kr"], "")
        contact_html = contacts.get(iso3, "")

        culture_ai = load_existing_culture_ai(iso3)
        if culture_ai is None and GOOGLE_API_KEY:
            culture_ai = generate_culture_ai(country["country_kr"], country["country_en"])
            time.sleep(4)

        detail = {
            "iso_code": iso3,
            "country_kr": country["country_kr"],
            "country_en": country["country_en"],
            "flag_image": flag_image,
            "travel_alert": {
                "level": country["alert_level"],
                "national_level": country["national_level"],
                "partial_level": country["partial_level"],
                "regions": country["alert_regions"],
            },
            "accident_info_html": accident_html,
            "local_contact_html": contact_html,
            "notice_url": NOTICE_FALLBACK_URL,
            "culture_ai": culture_ai,
        }

        with open(os.path.join(COUNTRIES_DIR, f"{iso3}.json"), "w", encoding="utf-8") as f:
            json.dump(detail, f, ensure_ascii=False, indent=2)

        countries_index.append({
            "iso_code": iso3,
            "country_kr": country["country_kr"],
            "country_en": country["country_en"],
            "lat": lat,
            "lng": lng,
            "flag_image": flag_image,
            "alert_level": country["alert_level"],
            "national_level": country["national_level"],
            "partial_level": country["partial_level"],
        })

    with open(os.path.join(DATA_DIR, "countries.json"), "w", encoding="utf-8") as f:
        json.dump(countries_index, f, ensure_ascii=False, indent=2)

    print(f"\nDone. {len(countries_index)} countries written to {DATA_DIR}")


if __name__ == "__main__":
    main()

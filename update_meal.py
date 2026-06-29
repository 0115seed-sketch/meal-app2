import os
import glob
import requests
import json
import re
from datetime import datetime, timezone, timedelta
from PIL import Image, ImageDraw, ImageFont

# 1. 고정 설정값
ATPT_CODE = "N10"
SCHUL_CODE = "8140253"
API_KEY = os.environ.get("NEIS_API_KEY", "")
USER_ID = "0115seed-sketch" 
REPO_NAME = "meal-app2"

# 2. 날짜 설정 (이번 주 월~금, 오늘)
KST = timezone(timedelta(hours=9))
today_dt = datetime.now(KST)
today_str = today_dt.strftime('%Y%m%d')
today_formatted = today_dt.strftime('%Y-%m-%d')

monday_dt = today_dt - timedelta(days=today_dt.weekday())
friday_dt = monday_dt + timedelta(days=4)
start_date = monday_dt.strftime('%Y%m%d')
end_date = friday_dt.strftime('%Y%m%d')

# 3. 데이터 정제 및 파싱 함수
def clean_dish_name(raw_name):
    # 정규표현식: 괄호와 그 안의 숫자/마침표 제거, 특수문자 제거
    cleaned = re.sub(r'\([0-9.]+\)', '', raw_name)
    cleaned = re.sub(r'[*#]', '', cleaned)
    return cleaned.strip()

def parse_nutrition(ntr_info_str):
    if not ntr_info_str:
        return {"carbs": 0, "protein": 0, "fat": 0}
    match_carbs = re.search(r'탄수화물\([^)]*\)\s*:\s*([0-9.]+)', ntr_info_str)
    match_protein = re.search(r'단백질\([^)]*\)\s*:\s*([0-9.]+)', ntr_info_str)
    match_fat = re.search(r'지방\([^)]*\)\s*:\s*([0-9.]+)', ntr_info_str)
    return {
        "carbs": float(match_carbs.group(1)) if match_carbs else 0,
        "protein": float(match_protein.group(1)) if match_protein else 0,
        "fat": float(match_fat.group(1)) if match_fat else 0
    }

# 4. 나이스 API 호출 (이번 주 전체 데이터)
url = (f"https://open.neis.go.kr/hub/mealServiceDietInfo"
       f"?KEY={API_KEY}&Type=json"
       f"&ATPT_OFCDC_SC_CODE={ATPT_CODE}&SD_SCHUL_CODE={SCHUL_CODE}"
       f"&MLSV_FROM_YMD={start_date}&MLSV_TO_YMD={end_date}"
       f"&MMEAL_SC_CODE=2")

weekly_data = {}
today_dishes = ["오늘의 중식 정보가 없습니다."]
today_summary = "중식 정보 없음"

try:
    res = requests.get(url).json()
    if "mealServiceDietInfo" in res:
        rows = res["mealServiceDietInfo"][1]["row"]
        for row in rows:
            ymd = row["MLSV_YMD"]
            raw_dishes = row["DDISH_NM"].split("<br/>")
            cleaned_dishes = [clean_dish_name(d) for d in raw_dishes if d.strip()]
            nutrients = parse_nutrition(row.get("NTR_INFO", ""))
            
            weekly_data[ymd] = {
                "date_formatted": f"{ymd[:4]}-{ymd[4:6]}-{ymd[6:]}",
                "dishes": cleaned_dishes,
                "nutrients": nutrients
            }
            
            # 오늘 데이터 분리 저장 (이미지 생성 및 요약용)
            if ymd == today_str:
                today_dishes = cleaned_dishes
                today_summary = ", ".join(cleaned_dishes)[:50] + "..."
                
except Exception as e:
    print(f"데이터 로드 실패: {str(e)}")

# 5. 충남 평균 데이터 읽기
chungnam_avg = {"carbs": 0, "protein": 0, "fat": 0}
try:
    if os.path.exists("chungnam_avg.json"):
        with open("chungnam_avg.json", "r", encoding="utf-8") as f:
            chungnam_avg = json.load(f)
except Exception as e:
    print(f"충남 평균 데이터 읽기 실패: {e}")

# 6. 이미지 폴더 관리 및 썸네일 생성 (오늘 급식 기준)
os.makedirs("images", exist_ok=True)
for old_img in glob.glob("images/meal_*.png"):
    try:
        os.remove(old_img)
    except Exception:
        pass

img = Image.new('RGB', (800, 400), color=(250, 252, 255))
d = ImageDraw.Draw(img)
d.rectangle([(0, 0), (800, 400)], outline=(220, 224, 230), width=4)
d.rectangle([(0, 0), (800, 15)], fill=(255, 212, 0))

try:
    font_title = ImageFont.truetype("NanumGothic.ttf", 28)
    font_content = ImageFont.truetype("NanumGothic.ttf", 20)
except Exception:
    font_title = ImageFont.load_default()
    font_content = ImageFont.load_default()

d.text((40, 45), f"오늘의 중식 ({today_formatted})", fill=(30, 30, 30), font=font_title)

y_offset = 110
for line in today_dishes:
    if y_offset > 350:
        d.text((40, y_offset), "...", fill=(120, 120, 120), font=font_content)
        break
    d.text((40, y_offset), f"• {line}", fill=(70, 72, 75), font=font_content)
    y_offset += 32

new_image_name = f"meal_{today_str}.png"
new_image_path = f"images/{new_image_name}"
img.save(new_image_path)

# 7. HTML 렌더링
og_image_url = f"https://{USER_ID}.github.io/{REPO_NAME}/{new_image_path}"
weekly_json_str = json.dumps(weekly_data, ensure_ascii=False)
avg_json_str = json.dumps(chungnam_avg, ensure_ascii=False)

with open("template.html", "r", encoding="utf-8") as f:
    template_content = f.read()

html_content = template_content\
    .replace("{{TODAY_YMD}}", today_str)\
    .replace("{{TODAY_FORMATTED}}", today_formatted)\
    .replace("{{MEAL_SUMMARY}}", today_summary)\
    .replace("{{OG_IMAGE_URL}}", og_image_url)\
    .replace("{{WEEKLY_DATA_JSON}}", weekly_json_str)\
    .replace("{{CHUNGNAM_AVG_JSON}}", avg_json_str)

with open("index.html", "w", encoding="utf-8") as f:
    f.write(html_content)

print(f"배포 완료: {new_image_name} 및 index.html 갱신 (주간 데이터 포함)")

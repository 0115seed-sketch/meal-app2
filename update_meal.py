import os
import glob
import requests
from datetime import datetime, timezone, timedelta
from PIL import Image, ImageDraw, ImageFont

# 1. 고정 설정값
ATPT_CODE = "N10"
SCHUL_CODE = "8140253"
API_KEY = "2af6977132b24eba82c8f17c111a605c"
USER_ID = "0115seed-sketch" 
REPO_NAME = "meal-app2"

# 2. 한국 시간(KST) 기준 날짜 구하기
KST = timezone(timedelta(hours=9))
today_dt = datetime.now(KST)
today = today_dt.strftime('%Y%m%d')
today_formatted = today_dt.strftime('%Y-%m-%d')

# 3. 나이스 API 호출 (중식)
url = f"https://open.neis.go.kr/hub/mealServiceDietInfo?KEY={API_KEY}&Type=json&ATPT_OFCDC_SC_CODE={ATPT_CODE}&SD_SCHUL_CODE={SCHUL_CODE}&MLSV_YMD={today}&MMEAL_SC_CODE=2"

meal_lines = []
try:
    res = requests.get(url).json()
    if "mealServiceDietInfo" in res:
        raw_text = res["mealServiceDietInfo"][1]["row"][0]["DDISH_NM"]
        meal_lines = raw_text.split("<br/>")
    else:
        meal_lines = ["오늘의 중식 정보가 없습니다."]
except Exception as e:
    meal_lines = [f"데이터 로드 실패: {str(e)}"]

meal_text = "\n".join(meal_lines)
meal_summary = ", ".join([line.split(" ")[0] for line in meal_lines if line])[:50] + "..."

# 4. 이미지 폴더 관리 (과거 이미지 삭제 및 폴더 생성)
os.makedirs("images", exist_ok=True)
for old_img in glob.glob("images/meal_*.png"):
    try:
        os.remove(old_img)
    except Exception:
        pass

# 5. 썸네일 이미지 동적 생성 (800x400)
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
for line in meal_lines:
    if y_offset > 350:
        d.text((40, y_offset), "...", fill=(120, 120, 120), font=font_content)
        break
    d.text((40, y_offset), f"• {line}", fill=(70, 72, 75), font=font_content)
    y_offset += 32

new_image_name = f"meal_{today}.png"
new_image_path = f"images/{new_image_name}"
img.save(new_image_path)

# 6. HTML 생성 (template.html 렌더링 및 index.html 생성)
og_image_url = f"https://{USER_ID}.github.io/{REPO_NAME}/{new_image_path}"

with open("template.html", "r", encoding="utf-8") as f:
    template_content = f.read()

html_content = template_content\
    .replace("{{DATE}}", today_formatted)\
    .replace("{{MEAL_TEXT}}", meal_text)\
    .replace("{{MEAL_SUMMARY}}", meal_summary)\
    .replace("{{OG_IMAGE_URL}}", og_image_url)

with open("index.html", "w", encoding="utf-8") as f:
    f.write(html_content)

print(f"배포 완료: {new_image_name} 및 index.html 갱신")

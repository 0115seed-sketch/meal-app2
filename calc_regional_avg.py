import os
import json
import random
import requests
import time
import re
from datetime import datetime, timezone, timedelta

# 설정값
ATPT_CODE = "N10" # 충남교육청
API_KEY = os.environ.get("NEIS_API_KEY")
SAMPLE_SIZE = 40

def get_current_week_dates():
    KST = timezone(timedelta(hours=9))
    today = datetime.now(KST)
    monday = today - timedelta(days=today.weekday())
    friday = monday + timedelta(days=4)
    return monday.strftime('%Y%m%d'), friday.strftime('%Y%m%d')

def parse_nutrition(ntr_info_str):
    if not ntr_info_str:
        return None
    
    nutrients = {}
    # 정규식을 통해 영양소 추출 (예: "탄수화물(g) : 115.5")
    match_carbs = re.search(r'탄수화물\([^)]*\)\s*:\s*([0-9.]+)', ntr_info_str)
    match_protein = re.search(r'단백질\([^)]*\)\s*:\s*([0-9.]+)', ntr_info_str)
    match_fat = re.search(r'지방\([^)]*\)\s*:\s*([0-9.]+)', ntr_info_str)
    
    if match_carbs and match_protein and match_fat:
        nutrients['carbs'] = float(match_carbs.group(1))
        nutrients['protein'] = float(match_protein.group(1))
        nutrients['fat'] = float(match_fat.group(1))
        return nutrients
    return None

def fetch_school_list():
    url = f"https://open.neis.go.kr/hub/schoolInfo?KEY={API_KEY}&Type=json&ATPT_OFCDC_SC_CODE={ATPT_CODE}&pSize=1000"
    try:
        res = requests.get(url).json()
        if "schoolInfo" in res:
            schools = res["schoolInfo"][1]["row"]
            return [school["SD_SCHUL_CODE"] for school in schools]
    except Exception as e:
        print(f"학교 목록 가져오기 실패: {e}")
    return []

def main():
    start_date, end_date = get_current_week_dates()
    print(f"주간 데이터 조회 기간: {start_date} ~ {end_date}")
    
    all_schools = fetch_school_list()
    if not all_schools:
        print("학교 목록을 불러오지 못했습니다.")
        return
        
    sampled_schools = random.sample(all_schools, min(SAMPLE_SIZE, len(all_schools)))
    print(f"선출된 학교 수: {len(sampled_schools)}개")
    
    total_carbs = 0
    total_protein = 0
    total_fat = 0
    valid_meal_count = 0
    
    for schul_code in sampled_schools:
        url = (f"https://open.neis.go.kr/hub/mealServiceDietInfo"
               f"?KEY={API_KEY}&Type=json"
               f"&ATPT_OFCDC_SC_CODE={ATPT_CODE}&SD_SCHUL_CODE={schul_code}"
               f"&MLSV_FROM_YMD={start_date}&MLSV_TO_YMD={end_date}"
               f"&MMEAL_SC_CODE=2") # 중식 강제
        
        try:
            res = requests.get(url).json()
            if "mealServiceDietInfo" in res:
                rows = res["mealServiceDietInfo"][1]["row"]
                for row in rows:
                    nutrients = parse_nutrition(row.get("NTR_INFO", ""))
                    if nutrients:
                        total_carbs += nutrients['carbs']
                        total_protein += nutrients['protein']
                        total_fat += nutrients['fat']
                        valid_meal_count += 1
            time.sleep(0.05) # API 부하 방지
        except Exception as e:
            continue
            
    avg_data = {
        "carbs": 0, "protein": 0, "fat": 0, "sample_count": valid_meal_count
    }
    
    if valid_meal_count > 0:
        avg_data["carbs"] = round(total_carbs / valid_meal_count, 1)
        avg_data["protein"] = round(total_protein / valid_meal_count, 1)
        avg_data["fat"] = round(total_fat / valid_meal_count, 1)
        
    print(f"계산 완료: {avg_data}")
    
    with open("chungnam_avg.json", "w", encoding="utf-8") as f:
        json.dump(avg_data, f, ensure_ascii=False, indent=2)

if __name__ == "__main__":
    main()

import streamlit as st
import requests
import google.generativeai as genai
from datetime import datetime
import pytz
import os
from dotenv import load_dotenv

load_dotenv()

# ===== 設定値 =====
GEMINI_MODEL = "gemini-3-flash-preview"

# ===== APIキーの読み込み =====
def get_gemini_key():
    try:
        return st.secrets["GEMINI_API_KEY"]
    except:
        return os.getenv("GEMINI_API_KEY")

GEMINI_API_KEY = get_gemini_key()

# ===== 天気・気温データを取得する関数 =====
def get_weather(lat, lon):
    url = "https://api.open-meteo.com/v1/forecast"
    params = {
        "latitude": lat,
        "longitude": lon,
        "current": ["temperature_2m", "weathercode"],
        "daily": [
            "temperature_2m_max",   # 当日最高気温
            "temperature_2m_min",   # 当日最低気温
        ],
        "past_days": 1,             # 前日データも取得
        "forecast_days": 1,
        "timezone": "auto"
    }
    response = requests.get(url, params=params)
    data = response.json()

    current_temp = data["current"]["temperature_2m"]
    code = data["current"]["weathercode"]

    # daily は [前日, 当日] の順で返ってくる
    today_max = data["daily"]["temperature_2m_max"][1]
    today_min = data["daily"]["temperature_2m_min"][1]
    yesterday_max = data["daily"]["temperature_2m_max"][0]
    yesterday_min = data["daily"]["temperature_2m_min"][0]

    # 前日比を計算
    diff_max = round(today_max - yesterday_max, 1)
    diff_min = round(today_min - yesterday_min, 1)

    return current_temp, code, today_max, today_min, diff_max, diff_min

# ===== 天気コードを日本語に変換 =====
def weather_description(code):
    if code == 0:
        return "快晴"
    elif code in [1, 2, 3]:
        return "曇り"
    elif code in [51, 53, 55, 61, 63, 65, 80, 81, 82]:
        return "雨"
    elif code in [71, 73, 75, 77, 85, 86]:
        return "雪"
    elif code in [95, 96, 99]:
        return "雷雨"
    else:
        return "不明"

# ===== 前日比を見やすく整形する関数 =====
def format_diff(diff):
    if diff > 0:
        return f"+{diff}℃"
    elif diff < 0:
        return f"{diff}℃"  # マイナスは自動でつく
    else:
        return "±0℃"

# ===== AIコメントを生成する関数 =====
def get_ai_comment(city, weather, temp, today_max, diff_max):
    if not GEMINI_API_KEY:
        return "⚠️ Gemini APIキーが設定されていません"

    genai.configure(api_key=GEMINI_API_KEY)
    model = genai.GenerativeModel(GEMINI_MODEL)

    # 前日比の表現を自然な言葉にする
    if diff_max > 3:
        diff_comment = f"昨日より{diff_max}℃も高く、かなり気温が上がっています"
    elif diff_max > 0:
        diff_comment = f"昨日より{diff_max}℃高めです"
    elif diff_max == 0:
        diff_comment = "昨日とほぼ同じ気温です"
    elif diff_max > -3:
        diff_comment = f"昨日より{abs(diff_max)}℃低めです"
    else:
        diff_comment = f"昨日より{abs(diff_max)}℃も低く、かなり気温が下がっています"

    prompt = f"""
あなたは親しみやすい天気コメンテーターです。
以下の天気情報を見て、その都市に住む人へ向けた
ひとこと感想・アドバイスを日本語で2〜3文で述べてください。
特に「気温の前日比」に触れてください。

都市: {city}
天気: {weather}
現在気温: {temp}℃
本日最高気温: {today_max}℃（{diff_comment}）
"""

    response = model.generate_content(prompt)
    return response.text

# ===== 画面を作る =====
st.title("🌍 天気コメンテーター")
st.caption("Gemini AIが今日の天気にひとこと添えます")

cities = {
    "東京": {"lat": 35.6762, "lon": 139.6503, "comment": True},
    "グルノーブル": {"lat": 45.1885, "lon": 5.7245, "comment": False},
}

for city_name, info in cities.items():
    st.subheader(f"📍 {city_name}")

    with st.spinner(f"{city_name}の天気を取得中..."):
        current_temp, code, today_max, today_min, diff_max, diff_min = get_weather(
            info["lat"], info["lon"]
        )
        weather = weather_description(code)

    # 現在気温・天気
    col1, col2 = st.columns(2)
    col1.metric("天気", weather)
    col2.metric("現在気温", f"{current_temp}℃")

    # 最高・最低気温＋前日比
    col3, col4 = st.columns(2)
    col3.metric("本日の最高気温", f"{today_max}℃", delta=format_diff(diff_max))
    col4.metric("本日の最低気温", f"{today_min}℃", delta=format_diff(diff_min))

    # AIコメント（東京のみ）
    if info["comment"]:
        with st.spinner("AIがコメントを考えています..."):
            comment = get_ai_comment(
                city_name, weather, current_temp, today_max, diff_max
            )
        st.info(f"💬 **AIコメント：** {comment}")

    st.divider()
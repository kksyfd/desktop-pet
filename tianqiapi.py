import geocoder
import requests
from datetime import datetime

def ip():
    ip_i=geocoder.ip('me')
    ip_chenshi=ip_i.city
    ip_zuobiao=ip_i.latlng
    return ip_chenshi,ip_zuobiao



def shuju_1(lat,lon):
    url='https://api.open-meteo.com/v1/forecast'

    params={
        "latitude": lat,  # 纬度：告诉 API 查哪个位置
        "longitude": lon,  # 经度：告诉 API 查哪个位置

        "current": [  # 【当前天气】我要这些实时数据
            "temperature_2m",  # 2米高度气温（标准气温）
            "relative_humidity_2m",  # 相对湿度
            "weather_code",  # 天气代码（晴/雨/雪等）
            "wind_speed_10m",  # 10米高度风速
            "apparent_temperature"  # 体感温度
        ],

        "daily": [  # 【每日预报】我要这些天的数据
            "temperature_2m_max",  # 每天最高温
            "temperature_2m_min",  # 每天最低温
            "weather_code"  # 每天天气状况
        ],

        "timezone": "auto",  # 自动根据经纬度判断时区
        "forecast_days": 3  # 预报未来3天（含今天）
    }

    try:
        response=requests.get(url,params=params,timeout=10)
        response.raise_for_status()
        return response.json()

    except requests.exceptions.RequestException as e:
        print(e)
        return None

def shuju_2(lat,lon):
    url='https://api.open-meteo.com/v1/forecast'

    params = {
        "latitude": lat,
        "longitude": lon,

        "hourly": [  # 【逐小时数据】
            "temperature_2m",  # 每小时气温
            "weather_code",  # 天气状况（晴/雨/雪）
            "precipitation",  # 降水量（毫米）
            "precipitation_probability",  # 降雨概率（%）
            "cloud_cover",  # 云量（%）
            "is_day",  # 是否是白天（1=白天，0=黑夜）
            "sunshine_duration",  # 日照时长（秒）
        ],

        "timezone": "auto",
        "forecast_days": 1  # 未来3天，每小时一条 = 72条数据
    }

    try:
        response=requests.get(url,params=params,timeout=10)
        response.raise_for_status()
        return response.json()

    except requests.exceptions.RequestException as e:
        print(e)
        return None

def ma(code):
    codas={
        0: "☀️ 晴",
        1: "🌤️ 大部晴朗", 2: "⛅ 多云", 3: "☁️ 阴天",
        45: "🌫️ 雾", 48: "🌫️ 雾凇",
        51: "🌦️ 毛毛雨", 53: "🌦️ 中度毛毛雨", 55: "🌧️ 密集毛毛雨",
        61: "🌧️ 小雨", 63: "🌧️ 中雨", 65: "🌧️ 大雨",
        71: "🌨️ 小雪", 73: "🌨️ 中雪", 75: "❄️ 大雪",
        80: "🌦️ 阵雨", 81: "🌧️ 中度阵雨", 82: "⛈️ 暴雨",
        95: "⛈️ 雷雨", 96: "⛈️ 雷雨伴冰雹", 99: "⛈️ 强雷雨伴冰雹"
    }
    return codas.get(code,f'未知天气(代码{code})')

def find_sunny_hours(data):
    """找出有太阳的时段"""
    hourly = data["hourly"]
    sunny = []
    for i in range(len(hourly["time"])):
        if hourly["is_day"][i] == 1 and hourly["cloud_cover"][i] < 30:
            sunny.append(hourly["time"][i])
    return sunny

def find_rainy_hours(data):
    """找出下雨的时段"""
    hourly = data["hourly"]
    rainy = []
    for i in range(len(hourly["time"])):
        if hourly["precipitation"][i] > 0:
            rainy.append({
                "time": hourly["time"][i],
                "rain": hourly["precipitation"][i],
                "prob": hourly["precipitation_probability"][i]
            })
    return rainy

def jiexi(data):
    if not data:
        return

    current=data['current']
    daily=data['daily']
    # 当前天气
    print("=" * 35)
    print(f"📍 位置：{data['latitude']:.2f}°N, {data['longitude']:.2f}°E")
    print(f"🕐 时间：{current['time']}")
    print(f"🌡️  温度：{current['temperature_2m']}°C")
    print(f"🤒 体感：{current['apparent_temperature']}°C")
    print(f"💧 湿度：{current['relative_humidity_2m']}%")
    print(f"💨 风速：{current['wind_speed_10m']} km/h")
    print(f"{ma(current['weather_code'])}")
    print("=" * 35)

    # 未来几天预报
    print("\n📅 未来预报：")
    for i in range(len(daily["time"])):
        date = daily["time"][i]
        max_temp = daily["temperature_2m_max"][i]
        min_temp = daily["temperature_2m_min"][i]
        code = daily["weather_code"][i]

        print(f"  {date} | {ma(code)} | {min_temp}°C ~ {max_temp}°C")

def xiangqin(data,sun,rany):
    if data:
        print(f'\n {"=" * 35}')
        print('出太阳')
        if sun:
            for t in sun:
                dt = datetime.fromisoformat(t)
                print(f"{dt.strftime('%m-%d %H:%M')}")
        else:
            print('最近没有天晴')

        print(f'\n {"=" * 35}')
        print('下雨')
        if rany:
            for r in rany:
                dt = datetime.fromisoformat(r['time'])
                print(f"{dt.strftime('%m-%d %H:%M')}| 降水{r['rain']}mm | 概率{r['prob']}%")
        else:
            print('最近不下雨')


def merge_weather_periods(data):
    print(f"\n{'=' * 40}")
    print("📅 逐小时天气（已合并）：")
    if data:
        """合并相邻相同天气的时段"""
        hourly = data["hourly"]
        times = hourly["time"]
        codes = hourly["weather_code"]
        rains = hourly["precipitation"]

        # 先构造 (时间, 天气描述) 的列表
        periods = []
        for i in range(len(times)):
            dt = datetime.fromisoformat(times[i])
            time_str = dt.strftime("%m-%d %H:%M")

            # 判断是晴还是雨（简化：只看有没有降水）
            if rains[i] > 0:
                weather = ma(codes[i])  # 有降水显示具体天气
            elif hourly["is_day"][i] == 1 and hourly["cloud_cover"][i] < 30:
                weather = "☀️ 晴"
            else:
                weather = ma(codes[i])  # 其他天气

            periods.append((time_str, weather, dt))

        # 合并相邻相同天气
        merged = []
        if not periods:
            return merged

        start_time = periods[0][0]
        start_dt = periods[0][2]
        current_weather = periods[0][1]

        for i in range(1, len(periods)):
            if periods[i][1] == current_weather:
                # 天气相同，继续当前段
                continue
            else:
                # 天气变了，保存上一段
                end_time = periods[i - 1][0]
                if start_time == end_time:
                    merged.append(f"{start_time} {current_weather}")
                else:
                    merged.append(f"{start_time}——{end_time} {current_weather}")

                # 开始新段
                start_time = periods[i][0]
                start_dt = periods[i][2]
                current_weather = periods[i][1]

        # 最后一段
        end_time = periods[-1][0]
        if start_time == end_time:
            merged.append(f"{start_time} {current_weather}")
        else:
            merged.append(f"{start_time}-{end_time} {current_weather}")

        return merged

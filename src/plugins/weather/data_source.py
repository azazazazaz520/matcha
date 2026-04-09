import requests
async def get_weather_of_city(city: str) -> str:
    id = "10015176"  
    key = "4ccd99765b0eae25690f23647f01be45"
    api_url = f"https://cn.apihz.cn/api/tianqi/tqyb.php?id={id}&key={key}&place={city}"
    
    try:
    # 发送GET请求
        response = requests.get(api_url)
        weather_data = response.json()
        if weather_data["code"] == 200:
            now = weather_data.get("nowinfo", {})
            temp = now.get("temperature", "未知")
            humidity = now.get("humidity", "未知")
            condition = weather_data.get("weather1", "未知")
            return f'📍 {city}当前天气：{condition}\n🌡️ 温度：{temp}℃\n💧 湿度：{humidity}%'
        else:
            return f'查询失败：{weather_data.get("msg", "未知错误")}'
    except Exception as e:
        return '请求异常'
    
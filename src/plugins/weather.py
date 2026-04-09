from nonebot import on_command, CommandSession
import json
import requests
@on_command('weather', aliases=('天气', '天气预报', '查天气'))
async def weather(session: CommandSession):
    city = session.current_arg_text.strip()
    if not city:
        city = (await session.aget(prompt='你想查询哪个城市的天气呢？')).strip()
        while not city:
            city = (await session.aget(prompt='要查询的城市名称不能为空呢，请重新输入')).strip()
    weather_report = await get_weather_of_city(city)
    await session.send(weather_report)


async def get_weather_of_city(city: str) -> str:
    id = "10015176"  
    key = "4ccd99765b0eae25690f23647f01be45"
    api_url = f"https://cn.apihz.cn/api/tianqi/tqyb.php?id={id}&key={key}&place={city}"
    
    
    
    try:
    # 发送GET请求
        response = requests.get(api_url)
        #print(f"接口返回状态码: {response.status_code}")
        #print(f"接口返回内容: {response.text}")
        weather_data = response.json()
        #print(f'正在查询{city}')
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
    
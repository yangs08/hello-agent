import os
import json
from datetime import datetime
from dotenv import load_dotenv
from langchain.agents.structured_output import ToolStrategy
from langchain.chat_models import init_chat_model
from langchain_core.messages import SystemMessage, HumanMessage
from langchain_core.tools import tool
from pydantic import BaseModel, Field
from typing_extensions import Literal

load_dotenv()

class WeatherInputData(BaseModel):
    city: str = Field(default="shanghai", description="城市名称")
    units: Literal["Celsius", "Fahrenheit"] = Field(description="温度单位", default="Celsius")
    time: str = Field(description="时间", default_factory=lambda: datetime.now().strftime("%H:%M:%S"))

class WeatherData(BaseModel):
    city: str = Field(description="城市名称")
    weather: str = Field(description="天气状况")
    temperature: int = Field(description="温度")
    description: str = Field(description="简短描述")
    timestamp: str = Field(default=None, description="时间戳")

    def model_post_init(self, __context):
        if self.timestamp is None:
            self.timestamp = datetime.now().isoformat()


@tool(args_schema=WeatherInputData)
def get_weather(city: str, units: str, time: str) -> str:
    """Get the weather for a given location."""

    if not city:
        city = "unknown"

    if units == "Celsius":
        temperature = 25
    else:
        temperature = 77
    return f"City: {city}, Units: {units}, Time: {time}, Weather: sunny, Temperature: {temperature}"


if __name__ == '__main__':
    deepseek_api_key = os.getenv("DEEPSEEK_API_KEY")
    if not deepseek_api_key:
        raise ValueError("DEEPSEEK_API_KEY is not set in .env file")

    print(f"DEEPSEEK_API_KEY loaded: {deepseek_api_key[:4]}...")

    model = init_chat_model("deepseek-v4-flash")

    # ====================
    # 示例1: 直接使用模型输出 JSON，并用 Pydantic 解析
    # ====================
    print("\n=== 示例1: 直接使用模型输出 JSON ===\n")

    system_prompt = """你是一个专业的结构化数据输出助手。
请严格按照以下 JSON 格式输出，不要包含任何额外的文本或解释：
{
  "city": "城市名称",
  "weather": "天气状况",
  "temperature": 温度(数字),
  "description": "简短描述",
  "timestamp": "时间戳"
}
"""

    messages = [
        SystemMessage(content=system_prompt),
        HumanMessage(content="请告诉我上海今天的天气")
    ]

    result = model.invoke(messages)
    print("原始输出:")
    print(result.content)

    try:
        weather_data = WeatherData.model_validate_json(result.content)
        print("\n解析后的结构体:")
        print(f"城市: {weather_data.city}")
        print(f"天气: {weather_data.weather}")
        print(f"温度: {weather_data.temperature}°C")
        print(f"描述: {weather_data.description}")
        print(f"时间: {weather_data.timestamp}")
        print("\n结构体转 JSON:")
        print(weather_data.model_dump_json(indent=2, ensure_ascii=False))
    except Exception as e:
        print(f"\n解析失败: {e}")

    # ====================
    # 示例2: 使用 agent 输出 JSON（不使用 response_format）
    # ====================
    print("\n\n=== 示例2: 使用 agent 输出 JSON ===\n")

    from langchain.agents import create_agent

    system_prompt_agent = """你是一个专业的天气数据助手。
请根据工具返回的结果，按照以下 JSON 格式输出：
{
  "city": "查询地点",
  "weather": "天气结果",
  "temperature": 温度(数字),
  "description": "描述",
  "timestamp": "时间戳"
}
不要包含任何额外文本。
"""

    my_agent = create_agent(model, tools=[get_weather])

    response = my_agent.invoke({
        "messages": [
            SystemMessage(content=system_prompt_agent),
            HumanMessage(content="查询北京的天气")
        ]
    })

    for message in response["messages"]:
        if hasattr(message, "content") and message.content:
            print("Agent 输出:")
            print(message.content)

            try:
                weather_data = WeatherData.model_validate_json(message.content)
                print("\n解析后的结构体:")
                print(f"城市: {weather_data.city}")
                print(f"天气: {weather_data.weather}")
                print(f"温度: {weather_data.temperature}°C")
            except Exception as e:
                print(f"\n解析失败: {e}")

    # ====================
    # 示例3: 使用 ToolStrategy 创建结构化输出的 agent
    # ====================
    print("\n\n=== 示例3: 使用 ToolStrategy 创建结构化输出的 agent ===\n")


    class AAAA(BaseModel):
        city: str = Field(description="城市名称")
        weather: str = Field(description="天气状况")
        temperature: int = Field(description="温度")
        description: str = Field(description="简短描述")
        timestamp: str = Field(default=None, description="时间戳")


    my_agent3 = create_agent(
        "deepseek-v4-flash",
        tools=[get_weather],
        response_format=ToolStrategy(AAAA),
    )

    response = my_agent3.invoke({
        "messages": [
            HumanMessage(content="查询广州的天气")
        ]
    })

    print("完整响应:")
    print(response)

    # response_format 会把结构化数据放在 structured_response 字段
    if "structured_response" in response:
        weather_data = response["structured_response"]
        print("\n解析后的结构体:")
        print(f"城市: {weather_data.city}")
        print(f"天气: {weather_data.weather}")
        print(f"温度: {weather_data.temperature}°C")
        print(f"描述: {weather_data.description}")
        print(f"时间: {weather_data.timestamp}")
        print("\n转 JSON:")
        print(weather_data.model_dump_json(indent=2, ensure_ascii=False))

    # 示例4: 手动创建结构体
    print("\n\n=== 示例4: 手动创建结构体 ===\n")

    manual_weather = WeatherData(
        city="深圳",
        weather="多云",
        temperature=30,
        description="今天深圳多云转晴"
    )
    print("手动创建的结构体:")
    print(f"manual_weather.city = {manual_weather.city}")
    print(f"manual_weather.weather = {manual_weather.weather}")
    print(f"manual_weather.temperature = {manual_weather.temperature}")
    print(f"manual_weather.timestamp = {manual_weather.timestamp}")
    print("\n转 JSON:")
    print(manual_weather.model_dump_json(indent=2, ensure_ascii=False))

"""
=======================================================
  Agent Demo - 用 Claude API 手动实现 AI Agent
=======================================================

【什么是 Agent？】
Agent（智能代理）= LLM（大语言模型）+ Tools（工具）+ Loop（循环）

核心思想：
  1. 给 LLM 提供一组"工具"（函数）
  2. LLM 自己决定：是直接回答，还是先调用某个工具
  3. 你执行工具、把结果返回给 LLM
  4. 重复这个过程，直到 LLM 觉得可以给出最终答案

【Agentic Loop 流程图】
  用户提问
      │
      ▼
  发送给 LLM（附带工具定义）
      │
      ▼
  LLM 决策 ──── stop_reason == "end_turn" ──► 输出最终答案 ──► 结束
      │
      │ stop_reason == "tool_use"
      ▼
  提取 tool_use 块（工具名 + 参数）
      │
      ▼
  你来执行工具函数（本地 Python 代码）
      │
      ▼
  把工具结果包装成 tool_result 消息
      │
      ▼
  重新发送给 LLM（带完整对话历史）
      │
      └──────────────────────────────────────► 回到 LLM 决策

【本 Demo 使用场景】
  一个"个人助手" Agent，具备以下工具：
  - get_current_time：获取当前时间
  - calculate：执行数学计算
  - get_weather：查询城市天气（模拟）
  - save_note：保存笔记到本地文件

【依赖】
  pip install anthropic
"""

import sys
import json
from dotenv import load_dotenv
load_dotenv()  # 自动读取 .env 文件中的环境变量
import math
import time
from datetime import datetime

# 设置 stdout 编码，避免 Windows 中文乱码
sys.stdout.reconfigure(encoding="utf-8")

import anthropic

# ============================================================
# 第一步：定义工具（Tools）
# ============================================================
# 每个工具由两部分组成：
#   1. "工具定义"（JSON Schema）——告诉 LLM 工具叫什么、能干什么、需要什么参数
#   2. "工具实现"（Python 函数）——真正执行工作的代码

# ---- 工具定义列表（发送给 LLM） ----
TOOLS = [
    {
        "name": "get_current_time",
        "description": "获取当前日期和时间。当用户询问时间、日期、今天星期几时使用。",
        "input_schema": {
            "type": "object",
            "properties": {
                "timezone": {
                    "type": "string",
                    "description": "时区，例如 'Asia/Shanghai'，默认为本地时间"
                }
            },
            "required": []  # 没有必填参数
        }
    },
    {
        "name": "calculate",
        "description": "执行数学计算。支持加减乘除、幂运算、平方根等。当用户要求计算数学题时使用。",
        "input_schema": {
            "type": "object",
            "properties": {
                "expression": {
                    "type": "string",
                    "description": "数学表达式，例如 '2 + 3 * 4'、'sqrt(16)'、'2 ** 10'"
                }
            },
            "required": ["expression"]  # expression 是必填参数
        }
    },
    {
        "name": "get_weather",
        "description": "查询指定城市的当前天气。当用户询问某个城市天气时使用。",
        "input_schema": {
            "type": "object",
            "properties": {
                "city": {
                    "type": "string",
                    "description": "城市名，例如 '北京'、'上海'、'London'"
                },
                "unit": {
                    "type": "string",
                    "enum": ["celsius", "fahrenheit"],
                    "description": "温度单位：celsius（摄氏度）或 fahrenheit（华氏度），默认 celsius"
                }
            },
            "required": ["city"]
        }
    },
    {
        "name": "save_note",
        "description": "把重要信息保存为本地笔记文件。当用户说'记录一下'、'帮我保存'、'写进笔记'时使用。",
        "input_schema": {
            "type": "object",
            "properties": {
                "title": {
                    "type": "string",
                    "description": "笔记标题"
                },
                "content": {
                    "type": "string",
                    "description": "笔记内容"
                }
            },
            "required": ["title", "content"]
        }
    }
]


# ============================================================
# 第二步：实现工具函数
# ============================================================

def get_current_time(timezone: str = "local") -> dict:
    """获取当前时间的工具实现"""
    now = datetime.now()
    return {
        "datetime": now.strftime("%Y-%m-%d %H:%M:%S"),
        "date": now.strftime("%Y年%m月%d日"),
        "time": now.strftime("%H:%M:%S"),
        "weekday": ["星期一", "星期二", "星期三", "星期四", "星期五", "星期六", "星期日"][now.weekday()],
        "timezone": timezone
    }


def calculate(expression: str) -> dict:
    """执行数学计算的工具实现"""
    # 安全说明：真实生产环境不要用 eval()，这里仅用于演示
    # 允许使用的数学函数
    safe_dict = {
        "sqrt": math.sqrt,
        "pow": math.pow,
        "abs": abs,
        "round": round,
        "pi": math.pi,
        "e": math.e,
        "sin": math.sin,
        "cos": math.cos,
        "tan": math.tan,
        "log": math.log,
        "log10": math.log10,
    }
    try:
        result = eval(expression, {"__builtins__": {}}, safe_dict)
        return {
            "expression": expression,
            "result": result,
            "formatted": f"{expression} = {result}"
        }
    except Exception as ex:
        return {
            "error": f"计算失败：{str(ex)}",
            "expression": expression
        }


def get_weather(city: str, unit: str = "celsius") -> dict:
    """
    查询天气的工具实现（使用 wttr.in 在线接口，免费无需 API key）

    接口地址：https://wttr.in/{城市名}?format=j1
    支持中文城市名，返回 JSON 格式的实时天气数据。
    """
    import requests
    from urllib.parse import quote

    try:
        # 对城市名进行 URL 编码，确保中文城市名正常传输
        city_encoded = quote(city)
        url = f"https://wttr.in/{city_encoded}?format=j1"
        # timeout=10 防止网络超时卡死
        resp = requests.get(url, timeout=10)
        resp.raise_for_status()  # 非 200 状态码直接抛异常
        data = resp.json()

        # 解析当前天气（current_condition 是列表，取第一项）
        current = data["current_condition"][0]

        temp_c = int(current["temp_C"])
        temp_f = int(current["temp_F"])

        # 根据 unit 参数决定返回摄氏或华氏
        if unit == "fahrenheit":
            temperature = f"{temp_f}°F"
        else:
            temperature = f"{temp_c}°C"

        # 天气描述（wttr.in 提供多语言，取第一个描述）
        condition = current["weatherDesc"][0]["value"]

        # 风速和风向
        wind_speed = current["windspeedKmph"]
        wind_dir   = current["winddir16Point"]

        # 从 nearest_area 获取实际解析到的城市名
        area = data["nearest_area"][0]
        resolved_city = area["areaName"][0]["value"]
        country       = area["country"][0]["value"]

        return {
            "city": f"{resolved_city}, {country}",
            "temperature": temperature,
            "feels_like": f"{current['FeelsLikeC']}°C",
            "condition": condition,
            "humidity": f"{current['humidity']}%",
            "wind": f"{wind_dir} {wind_speed}km/h",
            "visibility": f"{current['visibility']}km",
        }

    except requests.exceptions.Timeout:
        return {"error": f"查询 {city} 天气超时，请稍后重试"}
    except requests.exceptions.ConnectionError:
        return {"error": "网络连接失败，无法查询天气"}
    except (KeyError, IndexError) as e:
        return {"error": f"解析天气数据失败：{e}"}
    except Exception as e:
        return {"error": f"查询天气出错：{e}"}


def save_note(title: str, content: str) -> dict:
    """保存笔记的工具实现"""
    filename = "agent_notes.txt"
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    note_entry = f"\n{'=' * 50}\n[{timestamp}] {title}\n{'=' * 50}\n{content}\n"

    try:
        with open(filename, "a", encoding="utf-8") as f:
            f.write(note_entry)
        return {
            "success": True,
            "message": f"笔记已保存到 {filename}",
            "title": title,
            "timestamp": timestamp
        }
    except Exception as ex:
        return {"success": False, "error": str(ex)}


# ============================================================
# 第三步：工具分发器
# ============================================================
# 根据 LLM 给出的工具名称，调用对应的 Python 函数

def execute_tool(tool_name: str, tool_input: dict) -> str:
    """
    执行工具并返回结果（字符串格式）。
    LLM 的 tool_result 需要是字符串，所以我们用 json.dumps 序列化。
    """
    print(f"  [工具执行] {tool_name}({json.dumps(tool_input, ensure_ascii=False)})")

    if tool_name == "get_current_time":
        result = get_current_time(**tool_input)
    elif tool_name == "calculate":
        result = calculate(**tool_input)
    elif tool_name == "get_weather":
        result = get_weather(**tool_input)
    elif tool_name == "save_note":
        result = save_note(**tool_input)
    else:
        result = {"error": f"未知工具：{tool_name}"}

    result_str = json.dumps(result, ensure_ascii=False, indent=2)
    print(f"  [工具结果] {result_str}")
    return result_str


# ============================================================
# 第四步：Agent 主循环（Agentic Loop）
# ============================================================

def run_agent(user_question: str, client: anthropic.Anthropic, max_turns: int = 10) -> str:
    """
    核心 Agent 循环。

    参数：
        user_question: 用户的问题
        client:        anthropic SDK 客户端
        max_turns:     最大循环次数（防止无限循环）

    返回：
        LLM 最终给出的文字回答
    """
    print(f"\n{'═' * 60}")
    print(f"用户提问：{user_question}")
    print(f"{'═' * 60}")

    # ----------------------------------------------------------
    # 构建初始消息列表
    # messages 是整个对话的"记忆"，每轮都要带着完整历史发给 LLM
    # ----------------------------------------------------------
    messages = [
        {"role": "user", "content": user_question}
    ]

    # ----------------------------------------------------------
    # Agentic Loop：循环调用，直到 LLM 决定不再用工具
    # ----------------------------------------------------------
    for turn in range(max_turns):
        print(f"\n[第 {turn + 1} 轮] 调用 LLM... {messages}")

        # ---- 调用 LLM（含限速重试）----
        # 遇到 429 限速时，等待后自动重试，最多重试 3 次
        response = None
        for attempt in range(4):
            try:
                response = client.messages.create(
                    model="ppio/pa/claude-sonnet-4-6",  # 使用的模型（通过 PPIO 代理）
                    max_tokens=4096,                    # 最大输出 token 数
                    system=(
                        "你是一个智能助手，可以使用工具来帮助用户。"
                        "当你需要查询时间、计算数学、查询天气或保存笔记时，请使用对应的工具。"
                        "用中文回答用户的问题。"
                    ),
                    tools=TOOLS,                        # 把工具定义告诉 LLM
                    messages=messages                   # 带上完整的对话历史
                )
                break  # 成功则跳出重试循环
            except anthropic.RateLimitError:
                if attempt == 3:
                    raise  # 重试 3 次仍失败则向上抛出
                wait = 10 * (attempt + 1)  # 依次等待 10s / 20s / 30s
                print(f"  [限速] 触发 429，等待 {wait} 秒后重试（第 {attempt + 1}/3 次）...")
                time.sleep(wait)
        if response is None:
            return "[Agent 无法获取 LLM 响应]"

        print(f"[LLM 响应] stop_reason = {response.stop_reason}")

        # ---- 把 LLM 的回复加入消息历史 ----
        # 重要：必须把完整的 response.content（包含 tool_use 块）加入历史
        # 不能只加文本，否则 LLM 下次看不到自己调用了什么工具
        messages.append({
            "role": "assistant",
            "content": response.content  # 这是一个 content block 列表
        })

        # ============================================================
        # 判断 stop_reason：LLM 为什么停下来？
        # ============================================================

        print(f"response 的回复为 {response}")

        if response.stop_reason == "end_turn":
            # LLM 决定不再调用工具，给出了最终答案
            # 从 content blocks 中提取文本
            final_text = ""
            for block in response.content:
                if hasattr(block, "text"):
                    final_text += block.text

            print(f"\n{'─' * 60}")
            print(f"最终答案：\n{final_text}")
            print(f"{'─' * 60}")
            return final_text

        elif response.stop_reason == "tool_use":
            # LLM 决定调用一个或多个工具
            # 提取所有的 tool_use 块
            tool_results = []

            for block in response.content:
                # block.type 可能是 "text" 或 "tool_use"
                if block.type == "tool_use":
                    print(f"\n[LLM 决定调用工具] {block.name}")
                    print(f"  参数：{json.dumps(block.input, ensure_ascii=False)}")

                    # 执行工具，获取结果
                    result = execute_tool(block.name, block.input)

                    # 构造 tool_result，必须包含 tool_use_id（与 LLM 的请求对应）
                    tool_results.append({
                        "type": "tool_result",
                        "tool_use_id": block.id,   # 对应 LLM 发出的 tool_use.id
                        "content": result           # 工具执行结果（字符串）
                    })

                elif block.type == "text" and block.text:
                    # LLM 在调用工具前可能会先说一些话（思考过程）
                    print(f"  [LLM 思考] {block.text}")

            # 把工具结果作为 "user" 消息加入历史
            # 格式固定：role="user", content=tool_results 列表
            messages.append({
                "role": "user",
                "content": tool_results
            })

            # 继续循环，让 LLM 处理工具结果

        else:
            # 其他 stop_reason（如 max_tokens、stop_sequence 等）
            print(f"[警告] 意外的 stop_reason: {response.stop_reason}")
            break

    # 超过最大轮次
    return "[Agent 超过最大循环次数，未能完成任务]"


# ============================================================
# 第五步：主程序入口
# ============================================================

def main():
    # ---- 初始化 anthropic 客户端 ----
    # load_dotenv() 已在文件顶部将 .env 中的变量注入环境，
    # SDK 自动读取 ANTHROPIC_API_KEY 和 ANTHROPIC_BASE_URL。
    client = anthropic.Anthropic()

    print("=" * 60)
    print("        AI Agent Demo - 智能个人助手")
    print("=" * 60)
    print("可用工具：get_current_time / calculate / get_weather / save_note")
    print("输入 'quit' 退出\n")

    # ---- 预设演示问题（也可改为 input() 交互模式）----
    demo_questions = [
        # 单工具调用
        "现在几点了？",

        # 单工具调用，带参数
        "帮我计算 sqrt(144) + 2 ** 8 的结果",

        # 单工具调用
        "深圳今天天气怎么样？",

        # 多工具调用（LLM 可能在一轮内同时调用多个工具）
        "上海和广州今天的天气分别是多少度？",

        # 多步骤：先计算，再保存
        "计算圆周率 π 的值并保存到笔记，标题是'数学常数'",

        # 综合：时间 + 天气 + 保存
        "帮我记录一下：今天的日期和上饶天气。保存到笔记里，标题叫'今日备忘'",
    ]

    # 运行演示（问题之间等待 5 秒，避免触发 API 限速）
    for i, question in enumerate(demo_questions):
        if i > 0:
            print("等待 5 秒（避免限速）...")
            time.sleep(5)
        try:
            run_agent(question, client)
        except anthropic.RateLimitError:
            print(f"[限速] 触发 API 频率限制，跳过此问题。稍后重试。")
        except anthropic.BadRequestError as e:
            print(f"[请求错误] {e}")
        print()

    # ---- 可选：交互模式 ----
    # print("\n进入交互模式（输入 quit 退出）：")
    # while True:
    #     user_input = input("\n你: ").strip()
    #     if user_input.lower() in ("quit", "exit", "q"):
    #         break
    #     if user_input:
    #         run_agent(user_input, client)


if __name__ == "__main__":
    main()

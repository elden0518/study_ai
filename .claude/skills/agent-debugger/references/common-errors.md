# Agent 常见错误对照表

## HTTP 错误码

| 错误码 | 类型 | 常见原因 | 修复方法 |
|--------|------|---------|---------|
| 400 | BadRequestError | 消息格式错误、角色未交替、工具定义无效 | 检查 messages 列表格式 |
| 401 | AuthenticationError | API key 无效或未设置 | 检查 ANTHROPIC_API_KEY 环境变量 |
| 429 | RateLimitError | 请求频率超限（用户自身配额问题） | 指数退避重试，降低请求频率 |
| 500 | InternalServerError | 服务端临时故障 | 重试，等待后再试 |
| 529 | OverloadedError | Anthropic 服务端过载（非用户配额问题） | 与 429 相同处理：指数退避重试；注意与 429 区分，原因不同 |

---

## stop_reason 含义

| stop_reason | 含义 | 下一步操作 |
|-------------|------|-----------|
| `end_turn` | LLM 完成回答，不再调用工具 | 提取文本，结束循环 |
| `tool_use` | LLM 要调用工具 | 提取 tool_use blocks，执行工具，发回结果 |
| `max_tokens` | 达到 max_tokens 上限，输出被截断 | 增大 max_tokens 重试 |
| `stop_sequence` | 命中自定义停止序列 | 检查是否误设了 stop_sequences |

---

## 工具定义常见错误

### 错误 1：input_schema 缺少 type: object
```python
# ❌ 错误
"input_schema": {
    "properties": {"city": {"type": "string"}},
    "required": ["city"]
}

# ✅ 正确
"input_schema": {
    "type": "object",        # 必须有这行
    "properties": {"city": {"type": "string"}},
    "required": ["city"]
}
```

### 错误 2：工具名含特殊字符
```python
# ❌ 错误（含空格或中文）
"name": "查询 天气"

# ✅ 正确（只用字母、数字、下划线）
"name": "get_weather"
```

### 错误 3：description 为空或过短
```python
# ❌ 太模糊，LLM 不知道何时调用
"description": "天气"

# ✅ 明确说明触发条件
"description": "查询指定城市的实时天气。当用户询问天气、温度、降雨情况时使用。"
```

---

## 消息历史常见错误

### 错误 1：assistant 消息只保存了文本
```python
# ❌ 丢失了 tool_use block，下轮 API 会报错
messages.append({
    "role": "assistant",
    "content": response.content[0].text
})

# ✅ 保存完整的 content 列表
messages.append({
    "role": "assistant",
    "content": response.content
})
```

### 错误 2：tool_result 放错位置
```python
# ❌ 工具结果放在了 assistant 消息里
messages.append({
    "role": "assistant",
    "content": [{"type": "tool_result", ...}]
})

# ✅ 工具结果必须在 user 消息里
messages.append({
    "role": "user",
    "content": [{"type": "tool_result", "tool_use_id": "...", "content": "..."}]
})
```

### 错误 3：tool_use_id 不匹配
```python
# ❌ id 写错或遗漏
{"type": "tool_result", "tool_use_id": "wrong_id", "content": "结果"}

# ✅ 必须与 response 中 tool_use block 的 id 完全一致
for block in response.content:
    if block.type == "tool_use":
        {"type": "tool_result", "tool_use_id": block.id, "content": result}
```
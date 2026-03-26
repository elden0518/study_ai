# 消息历史格式规范

## 完整 Agentic Loop 消息流

```
Turn 1:
  user:      "北京天气怎么样？"

Turn 2 (LLM 决定调用工具):
  assistant: [TextBlock("好的，我来查"), ToolUseBlock(id="abc", name="get_weather", input={"city":"北京"})]

Turn 3 (工具结果返回):
  user:      [{"type":"tool_result", "tool_use_id":"abc", "content":"{...天气数据...}"}]

Turn 4 (LLM 给出最终答案):
  assistant: [TextBlock("北京今天晴天，18°C")]
```

## 合法消息格式速查

### 普通用户消息
```python
{"role": "user", "content": "用户的文字"}
```

### 工具调用轮（assistant）
```python
{
    "role": "assistant",
    "content": response.content   # List[TextBlock | ToolUseBlock]
                                  # 必须是原始 content 列表，不能序列化成字符串
}
```

### 工具结果轮（user）
```python
{
    "role": "user",
    "content": [
        {
            "type": "tool_result",
            "tool_use_id": "和上面 ToolUseBlock.id 完全一致",
            "content": "工具返回的字符串（建议用 json.dumps 序列化）",
            # 可选：
            "is_error": True   # 工具执行失败时设为 True
        }
    ]
}
```

## 并行工具调用格式

LLM 可能同时发出多个 ToolUseBlock，所有结果必须在同一条 user 消息里：

```python
# LLM 同时调用了 get_weather(上海) 和 get_weather(广州)
{
    "role": "user",
    "content": [
        {"type": "tool_result", "tool_use_id": "id_shanghai", "content": "..."},
        {"type": "tool_result", "tool_use_id": "id_guangzhou", "content": "..."}
    ]
}
```

## 消息交替规则

- 第一条消息必须是 `user`
- `user` 和 `assistant` 严格交替
- 不能连续出现两条相同角色的消息
- 工具结果消息角色是 `user`（不是 `tool`）
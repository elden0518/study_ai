---
name: Agent 调试助手
description: This skill should be used when the user asks to "调试 agent", "agent 报错", "工具调用失败", "agentic loop 异常", "stop_reason 不对", "消息历史出错", "tool_use 没有触发", "agent 死循环", "工具结果没被识别", "429 限速怎么处理", "tool not called", "tool not being triggered", "agent infinite loop", "agent not stopping", "rate limit 429", "message history error", "tool result not recognized", "agentic loop error", "stop_reason wrong". 提供基于 anthropic SDK 手动 agentic loop 的系统化调试方法。
version: 0.1.0
---

# Agent 调试助手

## 概述

针对使用 `anthropic` Python SDK 手动实现 agentic loop 时的常见问题，提供系统化诊断与修复方法。

适用场景：工具未被调用、循环不终止、消息历史格式错误、429 限速、工具结果未被识别等。

---

## 快速诊断流程

遇到 agent 问题时，按以下顺序逐步排查：

```
1. 打印 stop_reason          → 确认 LLM 是否意图调用工具
2. 打印完整 response.content → 确认工具调用块是否存在
3. 打印 messages 列表        → 确认消息历史格式是否正确
4. 单独测试工具函数           → 排除工具本身的 bug
5. 检查工具定义 JSON Schema  → 确认 LLM 能正确理解工具
```

---

## 核心调试代码片段

### 1. 打印完整 LLM 响应

```python
response = client.messages.create(...)

# 关键：先看 stop_reason
print(f"stop_reason: {response.stop_reason}")

# 再看每个 content block 的类型
for i, block in enumerate(response.content):
    print(f"block[{i}] type={block.type}")
    if block.type == "text":
        print(f"  text: {block.text}")
    elif block.type == "tool_use":
        print(f"  tool: {block.name}, input: {block.input}, id: {block.id}")
```

### 2. 打印消息历史（每轮循环）

```python
import json

def debug_messages(messages):
    for i, msg in enumerate(messages):
        role = msg["role"]
        content = msg["content"]
        if isinstance(content, str):
            print(f"[{i}] {role}: {content[:80]}")
        elif isinstance(content, list):
            for block in content:
                btype = block.get("type") if isinstance(block, dict) else block.type
                print(f"[{i}] {role} / {btype}")
```

### 3. 验证工具定义格式

使用 `scripts/check_tool_schema.py` 快速验证工具定义是否合法：

```bash
python .claude/skills/agent-debugger/scripts/check_tool_schema.py
```

---

## 五类常见问题与修复

### 问题一：工具从未被调用（stop_reason 始终是 end_turn）

**症状**：LLM 直接回答，不调用任何工具。

**排查**：
1. 检查工具 `description` 是否足够明确，告诉 LLM 何时使用
2. 检查用户问题与工具描述是否匹配
3. 尝试强制指定工具：`tool_choice={"type": "any"}`

**修复示例**：
```python
# 描述太模糊（LLM 不知道什么时候用）
"description": "查天气"

# 描述清晰（LLM 明确知道触发条件）
"description": "查询指定城市的实时天气。当用户询问某城市天气、温度、是否下雨时使用。"
```

---

### 问题二：消息历史格式错误（API 报 400）

**症状**：`anthropic.BadRequestError: roles must alternate`

**根本原因**：消息没有严格按 user → assistant → user → assistant 交替。

**正确格式**：
```python
# ✅ 工具调用后的正确消息追加方式
messages.append({
    "role": "assistant",
    "content": response.content   # 必须是完整的 content 列表，不能只取 text
})
messages.append({
    "role": "user",
    "content": [
        {
            "type": "tool_result",
            "tool_use_id": block.id,   # 必须与 tool_use block 的 id 对应
            "content": "工具返回的字符串结果"
        }
    ]
})
```

**常见错误**：
```python
# ❌ 只追加文本，丢失 tool_use block
messages.append({"role": "assistant", "content": response.content[0].text})

# ❌ tool_use_id 写错或遗漏
{"type": "tool_result", "content": result}  # 缺少 tool_use_id
```

---

### 问题三：Agent 死循环（超过 max_turns 仍未结束）

**症状**：循环一直运行，LLM 反复调用同一个工具。

**排查**：
1. 打印每轮的 `stop_reason` 和工具调用内容
2. 检查工具是否返回了 LLM 能利用的有效结果
3. 检查工具错误时是否正确返回了 `is_error: true`

**修复**：
```python
# 工具出错时明确告知 LLM
tool_results.append({
    "type": "tool_result",
    "tool_use_id": block.id,
    "content": f"错误：城市 '{city}' 不存在，请换一个城市重试",
    "is_error": True   # 告诉 LLM 这是错误，不要重复相同调用
})
```

---

### 问题四：429 限速错误

**症状**：`anthropic.RateLimitError: Error code: 429`

**标准修复模式（指数退避重试）**：
```python
import time, anthropic

for attempt in range(4):
    try:
        response = client.messages.create(...)
        break
    except (anthropic.RateLimitError, anthropic.InternalServerError):
        if attempt == 3:
            raise
        wait = 2 ** attempt * 10   # 10s → 20s → 40s（真正的指数退避）
        print(f"限速，等待 {wait}s 后重试...")
        time.sleep(wait)
```

---

### 问题五：并行工具调用结果未被识别

**症状**：LLM 同时发出两个 tool_use，但只处理了一个，第二个被忽略。

**正确处理方式**：一次性收集所有工具结果，放入同一个 user 消息：

```python
tool_results = []

for block in response.content:
    if block.type == "tool_use":
        result = execute_tool(block.name, block.input)
        tool_results.append({
            "type": "tool_result",
            "tool_use_id": block.id,
            "content": result
        })

# 所有结果在一条 user 消息里发回
messages.append({"role": "user", "content": tool_results})
```

---

## 参考资料

详细内容见：
- **`references/common-errors.md`** — 完整错误码对照表与修复方案
- **`references/message-format.md`** — 消息历史格式规范与反例

工具验证脚本：
- **`scripts/check_tool_schema.py`** — 自动检查工具定义是否符合 JSON Schema 规范
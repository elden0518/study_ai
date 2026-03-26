"""
工具定义校验脚本
用法：
  python .claude/skills/agent-debugger/scripts/check_tool_schema.py              # 默认读取 agent_demo.py
  python .claude/skills/agent-debugger/scripts/check_tool_schema.py my_agent.py  # 指定目标文件
"""
import re
import sys
import os

sys.path.insert(0, os.getcwd())
sys.stdout.reconfigure(encoding="utf-8")

CHECKS = []

def check(name, passed, detail=""):
    status = "✅" if passed else "❌"
    CHECKS.append((status, name, detail))

def validate_tools(tools):
    for i, tool in enumerate(tools):
        prefix = f"工具[{i}] '{tool.get('name', '?')}'"

        # 必须字段
        check(f"{prefix}: 有 name 字段",    "name" in tool)
        check(f"{prefix}: 有 description", "description" in tool and len(tool.get("description","")) > 5,
              "description 太短，LLM 可能不知道何时调用")
        check(f"{prefix}: 有 input_schema", "input_schema" in tool)

        schema = tool.get("input_schema", {})
        check(f"{prefix}: schema.type == 'object'", schema.get("type") == "object",
              f"实际值: {schema.get('type')}")
        check(f"{prefix}: schema 有 properties", "properties" in schema)

        # 工具名只允许字母、数字、下划线
        name = tool.get("name", "")
        check(f"{prefix}: name 格式合法", bool(re.match(r'^[a-zA-Z0-9_]+$', name)),
              f"名称 '{name}' 含有不合法字符（只允许字母/数字/下划线）")

        # required 字段必须在 properties 中存在
        required = schema.get("required", [])
        props = schema.get("properties", {})
        for req in required:
            check(f"{prefix}: required '{req}' 在 properties 中定义",
                  req in props, f"'{req}' 未在 properties 中找到")

def main():
    # 支持命令行参数指定目标文件，默认为 agent_demo
    target = sys.argv[1] if len(sys.argv) > 1 else "agent_demo.py"
    module_name = os.path.splitext(os.path.basename(target))[0]

    print("=" * 50)
    print("Agent 工具定义校验")
    print(f"目标文件：{target}")
    print("=" * 50)

    try:
        import importlib
        spec = importlib.util.spec_from_file_location(module_name, os.path.join(os.getcwd(), target))
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        tools = getattr(module, "TOOLS", None)
        if tools is None:
            print(f"❌ {target} 中未找到 TOOLS 变量")
            return
        print(f"找到 {len(tools)} 个工具定义\n")
        validate_tools(tools)
    except FileNotFoundError:
        print(f"❌ 找不到文件：{target}，请确认路径正确")
        return
    except Exception as e:
        print(f"❌ 无法加载 {target}：{e}")
        return

    # 打印结果
    passed = sum(1 for s, _, _ in CHECKS if s == "✅")
    failed = sum(1 for s, _, _ in CHECKS if s == "❌")

    for status, name, detail in CHECKS:
        line = f"  {status} {name}"
        if detail and status == "❌":   # 只有失败时才显示提示
            line += f"\n       提示: {detail}"
        print(line)

    print(f"\n结果：{passed} 通过，{failed} 失败")
    if failed == 0:
        print("✅ 所有工具定义格式正确！")
    else:
        print("❌ 请修复以上问题后重新运行")

if __name__ == "__main__":
    main()

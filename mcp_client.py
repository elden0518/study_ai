import asyncio
import sys
from pathlib import Path
from mcp import ClientSession, StdioServerParameters, stdio_client


async def main():
    # 启动 server 进程，通过 stdio 通信
    server_script = str(Path(__file__).parent / "mcp_server.py")
    server_params = StdioServerParameters(
        command=sys.executable,   # 使用当前 Python 解释器，跨平台兼容
        args=[server_script],     # 绝对路径，不依赖工作目录
    )

    async with stdio_client(server_params) as (read, write):
        async with ClientSession(read, write) as session:
            # 初始化
            await session.initialize()

            # 列出所有工具
            tools_result = await session.list_tools()
            print("=== 可用工具 ===")
            for tool in tools_result.tools:
                print(f"  - {tool.name}: {tool.description}")

            print()

            # 调用 add 工具
            result = await session.call_tool("add", {"a": 10, "b": 20})
            print("add(10, 20) =>", result.content[0].text)

            # 调用 multiply 工具
            result = await session.call_tool("multiply", {"a": 6, "b": 7})
            print("multiply(6, 7) =>", result.content[0].text)

            # 调用 greet 工具
            result = await session.call_tool("greet", {"name": "Claude"})
            print("greet('Claude') =>", result.content[0].text)


if __name__ == "__main__":
    asyncio.run(main())
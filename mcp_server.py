from mcp.server.fastmcp import FastMCP

mcp = FastMCP("计算器服务")

@mcp.tool()
def add(a: float, b: float) -> str:
    """计算两个数字的和，返回计算结果"""
    return str(a + b)

@mcp.tool()
def multiply(a: float, b: float) -> str:
    """计算两个数字的乘积，返回计算结果"""
    return str(a * b)

@mcp.tool()
def greet(name: str) -> str:
    """向指定名字的人打招呼"""
    return f"你好，{name}！欢迎使用 MCP Demo。"

if __name__ == "__main__":
    mcp.run(transport="stdio")
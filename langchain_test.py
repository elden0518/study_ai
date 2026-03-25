import sys; sys.stdout.reconfigure(encoding="utf-8")
from langchain.chat_models import init_chat_model
from langchain.agents import create_agent

def get_weather(city: str) -> str:
    """Get weather for a given city."""
    return f"It's always sunny in {city}!"

agent = create_agent(
    model="anthropic:ppio/pa/claude-sonnet-4-6",
    tools=[get_weather],
    system_prompt="You are a helpful assistant"
)

# Run the agent
response = agent.invoke(
    {"messages": [{"role": "user", "content": "what is the weather in sf"}]}
)
print(response["messages"][-1].content)

model = init_chat_model(
    "anthropic:ppio/pa/claude-sonnet-4-6",
    temperature=0
)

agent = create_agent(
    model=model,
    tools=[get_weather],
)
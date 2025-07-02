import asyncio
import os
from dotenv import load_dotenv

from langchain_groq import ChatGroq
from langchain_ollama import ChatOllama
from langchain_core.messages import BaseMessage, HumanMessage, AIMessage
from langgraph.graph.message import add_messages
from langgraph.checkpoint.memory import InMemorySaver
from langgraph.graph import StateGraph, START
from typing_extensions import Annotated, Sequence, TypedDict, Optional
from langchain_core.prompts.chat import ChatPromptTemplate
from langchain_mcp_adapters.client import MultiServerMCPClient  # type: ignore
from langgraph.prebuilt import create_react_agent


# Load environment variables
load_dotenv()
os.environ["GROQ_API_KEY"] = os.getenv("GROQ_API_KEY")

# Prompt Template
chat_prompt = ChatPromptTemplate.from_messages([
    ("system",
     "You are a helpful travel agent that helps users find flights. "
     "You will be provided with a JSON object containing flight search parameters. "
     "The JSON object will contain flight cards with details such as departure time, "
     "arrival time, airports, price, duration, number of stops, and airlines. "
     "Based on the provided flight cards, you will answer the user's question about flights. "
     "You also have to suggest the best flight based on the user's preferences. "
     "If there are no JSON objects, leave the schema blank and just answer the user's question. "
     "Keep your answers concise and relevant to the user's query."),
    ("placeholder", "{messages}")
])

# Language Model
llm = ChatGroq(model="deepseek-r1-distill-llama-70b")
# llm = ChatOllama(model="deepseek-r1:8b")

# Tool Loading
async def create_tools():
    client = MultiServerMCPClient({
        "flight": {
            "command": "python",
            "args": ["E:/Artificial Intelligence/mcp/travel_agent/Tools/search_flights_tool.py"],
            "transport": "stdio",
        }
    })
    return await client.get_tools()

class State(TypedDict):
    messages: Annotated[Sequence[BaseMessage], add_messages]
    flight_cards: Optional[dict[str, dict[str, str]]]

# LangGraph Node: LLM + Tools
async def call_model(state: State):
    tools = await create_tools()
    agent = create_react_agent(model=llm, tools=tools, prompt=chat_prompt)
    return await agent.ainvoke(state)

# LangGraph Flow
async def compile_graph():
    builder = StateGraph(State)
    builder.add_node("model", call_model)
    builder.add_edge(START, "model")
    memory = InMemorySaver()
    return builder.compile(checkpointer=memory)

# Main Chat Loop
async def main():
    graph = await compile_graph()
    print("✈️ Travel agent is ready. type 'exit' or 'quit' to terminate travel agent")
    print("-"*75)
    while True:
        user_input = input("User: ")
        if user_input.strip().lower() in ["exit", "quit"]:
            break
        input_messages = [HumanMessage(user_input)]
        try:
            response = await graph.ainvoke(
                {"messages":input_messages },
                config={"thread_id": "travel_agent"}
            )
            print(f"Agent : {response['messages'][-1].content}")
        except Exception as e:
            print("❌ Error in agent:", e)
              
# Run
if __name__ == "__main__":
    try:
        asyncio.run(main())
    except Exception as e:
        print("❌ Error:", e)
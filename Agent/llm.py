import asyncio
import os
from dotenv import load_dotenv

from langchain_groq import ChatGroq
from langchain_core.messages import BaseMessage, HumanMessage, AIMessage
from langgraph.graph.message import add_messages
from langgraph.checkpoint.memory import InMemorySaver
from langgraph.graph import StateGraph, START
from typing_extensions import Annotated, Sequence, TypedDict, Optional
from langchain_core.prompts.chat import ChatPromptTemplate
from langgraph.prebuilt import create_react_agent, chat_agent_executor
from langgraph.prebuilt import ToolNode, tools_condition
from tools import search_flights_tool
from langchain_core.tools import tool

# Load environment variables
load_dotenv()
os.environ["GROQ_API_KEY"] = os.getenv("GROQ_API_KEY")

# Prompt Template
chat_prompt = ChatPromptTemplate.from_messages([
    ("system",
     "You are a helpful travel agent that helps users find flights. "
     "Don't use search flights tool when user don't provide required parameters"
     "Keep your answers concise and relevant to the user's query."),
    ("placeholder", "{messages}")
])


# Language Model and tools
llm = ChatGroq(model="meta-llama/llama-4-maverick-17b-128e-instruct")
tools = [search_flights_tool]
memory = InMemorySaver()

# Agent
agent = create_react_agent(llm, tools, checkpointer=memory)

async def main():
    config = {"thread_id":"agent1", "recursion_limit":15}
    response = await agent.ainvoke({"messages":"Please provide me flight from Jakarta to Bali on August 20"}, config=config)
    print(response["messages"][-1].content)

if __name__ == "__main__":
    asyncio.run(main())




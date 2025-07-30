import asyncio
import os
from dotenv import load_dotenv

import groq
from langchain_groq import ChatGroq
from langgraph.checkpoint.memory import InMemorySaver
from langgraph.prebuilt import create_react_agent
from tools import search_flights_tool

# Load environment variables
load_dotenv()
os.environ["GROQ_API_KEY"] = os.getenv("GROQ_API_KEY")

# Language Model and tools
llm = ChatGroq(model="meta-llama/llama-4-maverick-17b-128e-instruct", temperature=0.3)
tools = [search_flights_tool]
memory = InMemorySaver()

# Agent
agent = create_react_agent(llm, tools, checkpointer=memory, prompt="You are a helpful TRAVEL PLANNNER")

async def main():
    print("type 'exit' or 'quit' to end the chat session")
    print("="*50)
    input_message = ""
    agent_no = 1
    while input_message != "quit" or input_message != "exit":
        input_message = input("🧑 User  : ")
        print()
        try:
            config = {"thread_id":f"agent{agent_no}", "recursion_limit":15}
            response = await agent.ainvoke({"messages":f"{input_message}"}, config=config)
            print(f"🤖 Agent : {response['messages'][-1].content}")
            print()
            if input_message == "quit" or input_message == "exit":
                break
        except groq.BadRequestError:
            print(f"🤖 Agent :parameters for tool did not match schema")
            print()
            agent_no += 1

        except groq.GraphRecursionError:
            print(f"🤖 Agent : I am sorry, I have tried my best to search your reservation")
            print()
            agent_no += 1

if __name__ == "__main__":
    asyncio.run(main())




import asyncio, os, sys
from dotenv import load_dotenv

import groq
from langchain_groq import ChatGroq
from langgraph.checkpoint.memory import InMemorySaver
from langgraph.prebuilt import create_react_agent

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from Agent.tools import search_flights_tool, get_flight_urls_tool, close_session_tool

# Load environment variables
load_dotenv()
os.environ["GROQ_API_KEY"] = os.getenv("GROQ_API_KEY")

# Language Model and tools
llm = ChatGroq(model="meta-llama/llama-4-maverick-17b-128e-instruct", temperature=0.3)
tools = [search_flights_tool, get_flight_urls_tool, close_session_tool]
memory = InMemorySaver()

SYSTEM_PROMPT = """You are a helpful TRAVEL PLANNER.
When a tool returns a list of flights, ALWAYS display them in a numbered list
(with the provided summaries) before asking the user to choose an index.
If a session_id is returned, keep it for follow-up tool calls."""

# Agent
agent = create_react_agent(llm, tools, checkpointer=memory, prompt=SYSTEM_PROMPT)

async def main():
    print("type 'exit' or 'quit' to end the chat session")
    print("="*50)
    input_message = ""
    agent_no = 1
    while input_message != "quit" or input_message != "exit":
        input_message = input("🧑 User  : ")
        print()
        try:
            config = {"thread_id":f"agent{agent_no}", "recursion_limit":10}
            response = await agent.ainvoke({"messages":f"{input_message}"}, config=config)
            print(f"🤖 Agent : {response['messages'][-1].content}")
            print()
            if input_message == "quit" or input_message == "exit":
                break
        except Exception as e:
            print(f"Error: {e}")
            print("Please try again or check your input.")

if __name__ == "__main__":
    asyncio.run(main())




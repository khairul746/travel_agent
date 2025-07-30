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

# Language Model and tools
llm = ChatGroq(model="meta-llama/llama-4-maverick-17b-128e-instruct", temperature=0.3)
tools = [search_flights_tool]
memory = InMemorySaver()

# Flight output schema
flight_details = {
  "type": "object",
  "patternProperties": {
    "^Flight \\d+$": {
      "type": "object",
      "properties": {
        "price": {
          "type": "string",
          "description": "The price of the flight, including currency symbol and formatting (e.g., 'Rp7,714,976')."
        },
        "stops": {
          "type": "integer",
          "description": "The number of stops for the flight (e.g., 0, 1, 2)."
        },
        "airlines": {
          "type": "array",
          "items": {
            "type": "string"
          },
          "description": "A list of airlines operating the flight (e.g., ['Scoot'])."
        },
        "departure_airport": {
          "type": "string",
          "description": "The full name of the departure airport (e.g., 'Singapore Changi Airport')."
        },
        "departure_time": {
          "type": "string",
          "description": "The departure time in AM/PM format (e.g., '7:50 AM')."
        },
        "departure_date": {
          "type": "string",
          "description": "The departure date in 'Day of Week, Month Day' format (e.g., 'Wednesday, August 20')."
        },
        "arrival_airport": {
          "type": "string",
          "description": "The full name of the arrival airport (e.g., 'Soekarno–Hatta International Airport')."
        },
        "arrival_time": {
          "type": "string",
          "description": "The arrival time in AM/PM format (e.g., '8:35 AM')."
        },
        "arrival_date": {
          "type": "string",
          "description": "The arrival date in 'Day of Week, Month Day' format (e.g., 'Wednesday, August 20')."
        },
        "flight_duration": {
          "type": "string",
          "description": "The total duration of the flight (e.g., '1 hr 45 min')."
        },
        "layovers": {
          "type": ["array", "null"],
          "items": {
            "type": "string"
          },
          "description": "A list of layover locations/details, or null if there are no layovers."
        }
      },
      "required": [
        "price",
        "stops",
        "airlines",
        "departure_airport",
        "departure_time",
        "departure_date",
        "arrival_airport",
        "arrival_time",
        "arrival_date",
        "flight_duration",
        "layovers"
      ],
      "additionalProperties": "false"
    }
  },
  "additionalProperties": "false"
}

# Prompt Template
chat_prompt = ChatPromptTemplate.from_messages([
    '''Answer the following questions as a PROFESSIONAL TRAVEL PLANNER.
    Answer the questions with interleaving THOUGHT, ACTION, and OBSERVATION steps.
    You have access to the following tools:

    {{search_flights_tool}}

    THOUGHT can reason about the current situation. and ACTION can be 3 types:
    (1) Tool Calling: Calling one of the tools provided.
    (2) Lookup [keyword] : which return the next sentence containing keyword in the current passage.
    (3) Finish [answer]: which returns the answer and finishes the task.
    ... (this Thought/Action/Action Input/Observation can repeat N times)
    
    Examples:
    1.
      Question : Hello, can you help me to find a flight from Jakarta to Kuala Lumpur on August 31?
      Thought : I need to search a flight from Jakarta to Kuala Lumpur on July 15.
      Action : search_flights_tool(origin='Jakarta', destination='Kuala Lumpur', departure_date='August 31')
      Observation : Here are some flights that I found {{flight_details}}

    2. 
      Question: I'm looking for round-trip flights from Jakarta to Singapore. I plan to depart on September 10 and return on September 17. I want business class for two adults and one child.
      Thought: I need to find round-trip flights from Jakarta to Singapore for two adults and one child, departing on September 10 and returning on September 17, and in business class.
      Action: search_flights_tool(origin='Jakarta', destination='Singapore', departure_date='September 10', return_date='September 17', adults=2, children=1, flight_class='Business')
      Observation: Here are some flights that I found {{flight_details}}
    3.
      Question: Search for one-way flights from Denpasar to Yogyakarta on October 20th. I'm traveling alone.
      Thought: I need to find one-way flights from Denpasar to Yogyakarta on October 20th for one adult passenger.
      Action: search_flights_tool(origin='Denpasar', destination='Yogyakarta', departure_date='October 20', flight_type='One-way', adults=1)
      Observation: Here are some flights that I found {{flight_details}}
    4. 
      Question: Can you find flights from Medan to Pekanbaru early next month?
      Thought: I need to find flights from Medan to Pekanbaru. However, 'early next month' isn't specific enough. I need to request a more specific departure date from the user.
      Action: Finish I need a more specific departure date for flights from Medan to Pekanbaru. Can you provide an exact date early next month?
    '''
])

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


asyncio.run(main())




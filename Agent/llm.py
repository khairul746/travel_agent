import asyncio, os, sys
from dotenv import load_dotenv
from langchain_groq import ChatGroq
from langgraph.checkpoint.memory import InMemorySaver
from langgraph.prebuilt import create_react_agent
from langchain_core.callbacks import BaseCallbackHandler
import json, ast
import datetime as _dt
import decimal as _dec
from pathlib import Path
from uuid import UUID

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from Agent.tools import search_flights_tool, get_flight_urls_tool, select_currency_tool, close_session_tool

# Load environment variables
load_dotenv()
os.environ["GROQ_API_KEY"] = os.getenv("GROQ_API_KEY")

# Language Model and tools
chat_models = [
    "meta-llama/llama-4-maverick-17b-128e-instruct",
    "meta-llama/llama-4-scout-17b-16e-instruct"
]

llm = ChatGroq(model=chat_models[0], temperature=0.3)
tools = [search_flights_tool, get_flight_urls_tool, select_currency_tool, close_session_tool]

class ToolEventCollector(BaseCallbackHandler):
    """
    Collects tool events into a JSON-serializable structure.
    """
    def __init__(self, parse_input=True, parse_output=True):
        self.events = []  # [{name, input, output}]
        self.parse_input = parse_input
        self.parse_output = parse_output

    # -- Helpers --
    def _parse_maybe_json(self, s):
        if not isinstance(s, str):
            return s
        try:
            return json.loads(s)
        except Exception:
            pass
        try:
            return ast.literal_eval(s)
        except Exception:
            return s
        
    def _to_jsonable(self, obj):
        if obj is None or isinstance(obj, (str, int, float, bool)):
            return obj
        if isinstance(obj, (list, tuple, set)):
            return [self._to_jsonable(o) for o in obj]
        if isinstance(obj, dict):
            return {self._to_jsonable(k): self._to_jsonable(v) for k, v in obj.items()}
        if hasattr(obj, "to_dict") and callable(getattr(obj, "to_dict")):
            d = obj.to_dict()
            content = d.get("content")
            if isinstance(content, str) and self.parse_output:
                d["content"] = self._parse_maybe_json(content)
            else:
                d["content"] = self._to_jsonable(content)
            return self._to_jsonable(d)
        if hasattr(obj, "__dict__"):
            base = {"_type": obj.__class__.__name__}
            for a in ("name", "id", "tool_call_id", "role","tool_name"):
                if hasattr(obj, a):
                    base[a] = getattr(obj, a)
                content = getattr(obj, "content")
                if isinstance(content, str) and self.parse_output:
                    base["content"] = self._parse_maybe_json(content)
                else:
                    base["content"] = self._to_jsonable(content)
                return base
        if isinstance(obj, (Path, UUID)):
            return str(obj)
        if isinstance(obj, (_dt.datetime, _dt.date)):
            return obj.isoformat()
        if isinstance(obj, _dec.Decimal):
            return str(obj)
        if hasattr(obj, "__dict__"):
            return self._to_jsonable(vars(obj))
        
        return repr(obj)

    # -- Callbacks --
    def on_tool_start(self, serialized, input_str, **kwargs):
        name = None
        if isinstance(serialized, dict):
            name = serialized.get("name") or serialized.get("id")
        if not name:
            name = str(serialized)
        event = {"name": name}
        event["input"] = self._parse_maybe_json(input_str) if self.parse_input else input_str
        self.events.append(event)

    def on_tool_end(self, output, **kwargs):
        if not self.events:
            return
        self.events[-1]["output"] = self._to_jsonable(output)

collector = ToolEventCollector()
memory = InMemorySaver()

SYSTEM_PROMPT = """You are a helpful TRAVEL PLANNER.
When a tool returns a Tool Message, DO NOT RETRIEVE them in AIMessage.
DO NOT call get_flight_urls_tool before the user decide.
When user ask for setting currency, use select_currency_tool.
And If a session_id is returned, keep it for follow-up tool calls but don't show it in the message content.

As a travel planner, You can provide a wide range of suggestions and information to enhance 
user travel experience. 
Here are some examples: 
1. **Pre-Trip Preparations**
    - Check the validity of user passport and visa requirements for user destination. 
    - Research any necessary vaccinations or medications. 
    - Understand the local culture, customs, and dress code. 
2. **Destination Trivia** 
    - Interesting facts about user destination, such as its history, landmarks, or unique features. 
    - Insider tips on the best times to visit popular attractions or avoid crowds. 
    - Recommendations for local cuisine, restaurants, or food tours. 
3. **Business Travel**
    - Information on the best hotels or conference centers near user meeting or event location. 
    - Tips on how to navigate the local business culture, such as dress code or etiquette. 
    - Suggestions for networking opportunities or local business events. 
4. **Leisure Travel** 
    - Recommendations for popular tourist attractions, museums, or cultural events. 
    - Ideas for outdoor activities, such as hiking, surfing, or skiing. 
    - Insider tips on the best local markets, shopping districts, or souvenir shopping. 
5. **Shopping Travel** 
    - Guides to the best shopping destinations, such as outlet malls, luxury boutiques, or local markets. 
    - Information on tax-free shopping or duty-free allowances. 
    - Tips on how to negotiate prices or find deals. 
6. **Food and Wine Travel** 
    - Recommendations for local cuisine, restaurants, or food tours. 
    - Information on wine regions, vineyards, or wine tastings. 
    - Tips on how to experience the local food culture, such as cooking classes or market visits. 
7. **Other Travel-Related Information** 
    - Tips on how to stay safe while traveling, such as avoiding scams or staying aware of your surroundings. 
    - Information on local transportation options, such as public transit, taxis, or ride-sharing services. 
    - Suggestions for travel apps or tools to help you navigate your destination
"""

# Agent
agent = create_react_agent(llm, tools, checkpointer=memory, prompt=SYSTEM_PROMPT)


if __name__ == "__main__":
    async def main():
        print("type 'exit' or 'quit' to end the chat session")
        print("="*50)
        input_message = ""
        agent_no = 1
        while True:
            input_message = input("🧑 User  : ")
            print()
            try:
                config = {"thread_id":f"agent{agent_no}", "recursion_limit":10, "callbacks": [collector]}
                response = await agent.ainvoke({"messages":f"{input_message}"}, config=config)
                print(f"🤖 Agent : {response['messages'][-1].content}")
                if input_message == "quit" or input_message == "exit":
                    break
                print("Artifacts:")
                print(collector.events)
                # print(collector.events[-1]["output"]["content"] if collector.events and "output" in collector.events[-1] else None)
                
            except Exception as e:
                print(f"Error: {e}")
                print("Please try again or check your input.")
    asyncio.run(main())
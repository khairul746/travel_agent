from flask import Flask, request, jsonify, render_template
from flask_cors import CORS
import asyncio
from Agent.llm import agent

app = Flask(__name__)
CORS(app)

@app.route("/")
def main():
    return render_template("index.html")

@app.route("/chat", methods=["POST"])
def chat():
    user_input = request.json.get("message", "")
    response = asyncio.run(run_agent(user_input))
    return jsonify({"reply": response})

async def run_agent(input_message):
    agent_no = 1
    config = {"thread_id": f"agent{agent_no}", "recursion_limit": 15}
    response = await agent.ainvoke({"messages": input_message}, config=config)
    return response['messages'][-1].content

if __name__ == "__main__":
    app.run(debug=True)


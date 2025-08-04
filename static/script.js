async function sendMessage() {
  const input = document.getElementById("userInput");
  const msg = input.value.trim();
  if (msg === "") return;

  const chatBox = document.getElementById("chatMessages");

  const userBubble = document.createElement("div");
  userBubble.className = "chat-bubble user-bubble";
  userBubble.textContent = msg;
  chatBox.prepend(userBubble);

  input.value = "";

  try {
    const response = await fetch("/chat", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ message: msg }),
    });

    const data = await response.json();

    const botBubble = document.createElement("div");
    botBubble.className = "chat-bubble bot-bubble";
    botBubble.textContent = data.reply;
    chatBox.prepend(botBubble);
  } catch (err) {
    const errorBubble = document.createElement("div");
    errorBubble.className = "chat-bubble bot-bubble";
    errorBubble.textContent = "⚠️ Could not connect to the server.";
    chatBox.prepend(errorBubble);
  }
}

function handleKeyDown(event) {
  if (event.key === "Enter") {
    event.preventDefault();
    sendMessage();
  }
}

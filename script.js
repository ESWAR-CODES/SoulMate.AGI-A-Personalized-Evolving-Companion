document.addEventListener("DOMContentLoaded", () => {
  const backendURL = "https://soulmate-agi.onrender.com";

  const chatBox = document.getElementById('chat');
  const userInput = document.getElementById('userInput');
  const summaryText = document.getElementById('summaryText');
  const wellnessResult = document.getElementById('wellnessResult');

  function addMessage(sender, text) {
    const msg = document.createElement('div');
    msg.className = 'message ' + sender.toLowerCase();
    msg.textContent = sender + ': ' + text;
    chatBox.appendChild(msg);
    chatBox.scrollTop = chatBox.scrollHeight;
    if (sender === 'Bot') speakText(text);
  }

  function sendMessage() {
    const text = userInput.value.trim();
    if (!text) return;
    addMessage('User', text);
    userInput.value = '';

    fetch(`${backendURL}/chat`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ message: text })
    })
    .then(res => res.json())
    .then(data => {
      const botReply = data.reply || "Sorry, I didn’t understand that.";
      const mood = data.emotion || "😐 Neutral";
      addMessage('Bot', `${botReply} (Mood: ${mood})`);
    })
    .catch(err => {
      console.error(err);
      addMessage('Bot', "Sorry, I couldn't connect to the server.");
    });
  }

  function speakText(text) {
    const speech = new SpeechSynthesisUtterance(text);
    speechSynthesis.speak(speech);
  }

  function startVoiceInput() {
    const recognition = new (window.SpeechRecognition || window.webkitSpeechRecognition)();
    recognition.lang = 'en-US';
    recognition.start();
    recognition.onresult = function(event) {
      const transcript = event.results[0][0].transcript;
      userInput.value = transcript;
      sendMessage();
    };
  }

  function saveJournal() {
    const journalText = document.getElementById('journalInput').value.trim();
    if (!journalText) return;

    fetch(`${backendURL}/journal`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ entry: journalText })
    })
    .then(res => res.json())
    .then(() => {
      alert('Journal saved.');
      document.getElementById('journalInput').value = '';
    })
    .catch(err => {
      console.error(err);
      alert("Failed to save journal.");
    });
  }

  function getSummary() {
    fetch(`${backendURL}/summary`)
      .then(res => res.json())
      .then(data => {
        summaryText.textContent = `Today's dominant mood is ${data.mood_summary} (based on ${data.entries} entries).`;
      })
      .catch(() => {
        summaryText.textContent = "Failed to fetch summary.";
      });
  }

  function getWellness() {
    fetch(`${backendURL}/wellness`)
      .then(res => res.json())
      .then(data => {
        wellnessResult.textContent = data.status 
          ? data.status 
          : `Wellness Score: ${data.wellness_score} / 100 | Loneliness Risk: ${data.loneliness_risk}`;
      })
      .catch(() => {
        wellnessResult.textContent = "Failed to check wellness.";
      });
  }

  document.getElementById("sendBtn").onclick = sendMessage;
  document.getElementById("voiceBtn").onclick = startVoiceInput;
  document.getElementById("saveJournalBtn").onclick = saveJournal;
  document.getElementById("getSummaryBtn").onclick = getSummary;
  document.getElementById("checkWellnessBtn").onclick = getWellness;
});

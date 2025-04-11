from flask import Flask, request, jsonify
import openai
import faiss
import numpy as np
from textblob import TextBlob
import os
import json
from datetime import datetime

app = Flask(__name__)
openai.api_key = os.getenv("OPENAI_API_KEY")

# Initialize FAISS index
embedding_dim = 1536
index = faiss.IndexFlatL2(embedding_dim)
memory = []

def get_embedding(text):
    response = openai.Embedding.create(
        input=[text],
        model="text-embedding-ada-002"
    )
    return np.array(response['data'][0]['embedding'])

def analyze_sentiment(text):
    blob = TextBlob(text)
    return blob.sentiment.polarity

@app.route('/chat', methods=['POST'])
def chat():
    data = request.get_json()
    user_message = data['message']
    timestamp = datetime.now().isoformat()

    # Embedding and indexing
    embedding = get_embedding(user_message)
    index.add(np.array([embedding]))
    memory.append(user_message)

    # Emotion analysis
    sentiment = analyze_sentiment(user_message)
    emotion = "Positive" if sentiment > 0 else "Negative" if sentiment < 0 else "Neutral"

    # Chat reply
    response = openai.ChatCompletion.create(
        model="gpt-3.5-turbo",
        messages=[{"role": "user", "content": user_message}]
    )
    reply = response['choices'][0]['message']['content']

    # Store in memory file
    memory_data = {
        "timestamp": timestamp,
        "user": user_message,
        "bot": reply,
        "emotion": emotion,
        "embedding_id": len(memory) - 1
    }
    with open("memory.jsonl", "a") as f:
        f.write(json.dumps(memory_data) + "\n")

    return jsonify({'reply': reply, 'emotion': emotion})

@app.route('/journal', methods=['POST'])
def journal():
    data = request.get_json()
    entry = data['entry']
    timestamp = datetime.now().isoformat()
    with open('journal.json', 'a') as f:
        json.dump({'timestamp': timestamp, 'entry': entry}, f)
        f.write('\n')
    return jsonify({'status': 'saved'})

@app.route('/summary', methods=['GET'])
def summary():
    moods = {'Positive': 0, 'Negative': 0, 'Neutral': 0}
    count = 0
    if os.path.exists('journal.json'):
        with open('journal.json', 'r') as f:
            for line in f:
                entry = json.loads(line)
                sentiment = analyze_sentiment(entry['entry'])
                emotion = "Positive" if sentiment > 0 else "Negative" if sentiment < 0 else "Neutral"
                moods[emotion] += 1
                count += 1
    dominant_mood = max(moods, key=moods.get) if count > 0 else "Neutral"
    return jsonify({'mood_summary': dominant_mood, 'entries': count})

@app.route('/train', methods=['POST'])
def train():
    if not os.path.exists("memory.jsonl"):
        return jsonify({"status": "No memory found to train."})

    with open("memory.jsonl", "r") as f:
        conversations = [json.loads(line) for line in f]

    messages = [{"role": "system", "content": "You are an AI assistant that builds personality profiles from chat history."}]
    for convo in conversations[-30:]:
        messages.append({"role": "user", "content": convo["user"]})
        messages.append({"role": "assistant", "content": convo["bot"]})

    messages.append({
        "role": "user",
        "content": "Based on our conversations, what can you tell about me? Summarize my personality, preferences, emotions, and communication style."
    })

    response = openai.ChatCompletion.create(
        model="gpt-3.5-turbo",
        messages=messages
    )

    profile = response['choices'][0]['message']['content']

    with open("profile.json", "w") as f:
        json.dump({
            "timestamp": datetime.now().isoformat(),
            "summary": profile
        }, f, indent=2)

    return jsonify({"status": "Profile trained", "summary": profile})

@app.route('/wellness', methods=['GET'])
def wellness():
    if not os.path.exists("journal.json"):
        return jsonify({"status": "No journal entries found."})

    entries = []
    with open('journal.json', 'r') as f:
        for line in f:
            data = json.loads(line)
            entries.append(data)

    if not entries:
        return jsonify({"status": "No data"})

    mood_scores = []
    keyword_hits = 0
    lonely_keywords = ["lonely", "alone", "isolated", "ignored", "no one", "quiet", "bored", "unheard"]

    for entry in entries[-10:]:
        text = entry["entry"]
        polarity = analyze_sentiment(text)
        mood_scores.append(polarity)

        if any(word in text.lower() for word in lonely_keywords):
            keyword_hits += 1

    avg_mood = sum(mood_scores) / len(mood_scores)
    wellness_score = round((avg_mood + 1) * 50)  # scale: -1 to +1 → 0 to 100
    loneliness_risk = "High" if keyword_hits >= 5 else "Moderate" if keyword_hits >= 2 else "Low"

    return jsonify({
        "wellness_score": wellness_score,
        "loneliness_risk": loneliness_risk,
        "entries_analyzed": len(mood_scores)
    })

if __name__ == '__main__':
    app.run(debug=True)

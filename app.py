from flask import Flask, request, jsonify
from flask_cors import CORS
import openai
import faiss
import numpy as np
from textblob import TextBlob
import os
import json
from datetime import datetime

app = Flask(__name__)
CORS(app)

openai.api_key = os.getenv("OPENAI_API_KEY")

# FAISS memory setup
embedding_dim = 1536
index = faiss.IndexFlatL2(embedding_dim)
memory = []

# ---------- UTILITY FUNCTIONS ----------

def get_embedding(text):
    response = openai.Embedding.create(
        input=[text],
        model="text-embedding-ada-002"
    )
    return np.array(response['data'][0]['embedding'])

def analyze_sentiment(text):
    blob = TextBlob(text)
    return blob.sentiment.polarity

def mood_label(score):
    return "Positive" if score > 0 else "Negative" if score < 0 else "Neutral"

# ---------- CHAT ENDPOINT ----------

@app.route('/chat', methods=['POST'])
def chat():
    data = request.get_json()
    user_message = data['message']

    embedding = get_embedding(user_message)
    index.add(np.array([embedding]))
    memory.append(user_message)

    sentiment = analyze_sentiment(user_message)
    emotion = mood_label(sentiment)

    recent_moods = [analyze_sentiment(m) for m in memory[-10:]]
    avg_mood = sum(recent_moods) / len(recent_moods) if recent_moods else 0
    mood_state = "happy 😊" if avg_mood > 0.2 else "down 😔" if avg_mood < -0.2 else "neutral 😐"

    mood_prompt = (
        "You are SoulMate.AGI, a compassionate and supportive AI friend. "
        f"The user has been feeling {mood_state} lately. Respond in a helpful and caring way."
    )

    response = openai.ChatCompletion.create(
        model="gpt-3.5-turbo",
        messages=[
            {"role": "system", "content": mood_prompt},
            {"role": "user", "content": user_message}
        ]
    )
    reply = response['choices'][0]['message']['content']
    return jsonify({'reply': reply, 'emotion': emotion})

# ---------- JOURNAL ENDPOINT ----------

@app.route('/journal', methods=['POST'])
def journal():
    data = request.get_json()
    entry = data['entry']
    timestamp = datetime.now().isoformat()

    journal_data = {'timestamp': timestamp, 'entry': entry}
    with open('journal.json', 'a') as f:
        json.dump(journal_data, f)
        f.write('\n')

    return jsonify({'status': 'saved', 'entry': journal_data})

# ---------- SUMMARY ENDPOINT ----------

@app.route('/summary', methods=['GET'])
def summary():
    moods = {'Positive': 0, 'Negative': 0, 'Neutral': 0}
    count = 0

    if os.path.exists('journal.json'):
        with open('journal.json', 'r') as f:
            for line in f:
                entry = json.loads(line)
                sentiment = analyze_sentiment(entry['entry'])
                emotion = mood_label(sentiment)
                moods[emotion] += 1
                count += 1

    if count == 0:
        return jsonify({'mood_summary': 'No data yet', 'entries': 0})

    dominant_mood = max(moods, key=moods.get)
    return jsonify({'mood_summary': dominant_mood, 'entries': count})

# ---------- WELLNESS CHECK ENDPOINT ----------

@app.route('/wellness', methods=['GET'])
def wellness():
    if not os.path.exists('journal.json'):
        return jsonify({'status': 'No journal data yet.'})

    mood_scores = []
    with open('journal.json', 'r') as f:
        for line in f:
            entry = json.loads(line)
            score = analyze_sentiment(entry['entry'])
            mood_scores.append(score)

    if not mood_scores:
        return jsonify({'status': 'No journal entries yet.'})

    avg_score = sum(mood_scores) / len(mood_scores)
    wellness_score = round((avg_score + 1) * 50)  # Convert -1~1 to 0~100
    loneliness_risk = "High" if avg_score < -0.2 else "Moderate" if avg_score < 0.2 else "Low"

    return jsonify({
        'wellness_score': wellness_score,
        'loneliness_risk': loneliness_risk
    })

# ---------- RUN ----------

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)

from flask import Flask, jsonify
from sporex_analyzer import generate_analysis
from news_fetcher import get_random_news

app = Flask(__name__)

@app.route("/api/analyze", methods=["GET"])
def analyze_news():
    article, topic = get_random_news()
    if not article:
        return jsonify({"error": f"Aucune actualité trouvée sur {topic}"}), 404
    analysis = generate_analysis(article["title"], topic)
    return jsonify({
        "title": article["title"],
        "source": article["source"],
        "url": article["url"],
        "topic": topic,
        "analysis": analysis
    })

if __name__ == "__main__":
    app.run(debug=True)

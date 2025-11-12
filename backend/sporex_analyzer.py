import requests
from bs4 import BeautifulSoup
import json

def fetch_data(url):
    response = requests.get(url)
    response.raise_for_status()
    return response.text

def process_data(raw_html):
    soup = BeautifulSoup(raw_html, 'html.parser')
    # Exemple : extraire tous les titres d’articles
    titles = [h2.get_text() for h2 in soup.find_all('h2')]
    return titles

def generate_analysis(data):
    # Exemple simple : compter les titres
    analysis = {
        'total_titles': len(data),
        'titles': data
    }
    return analysis

def save_analysis(analysis, filename='analysis.json'):
    with open(filename, 'w') as f:
        json.dump(analysis, f, indent=4)

def load_analysis(filename='analysis.json'):
    with open(filename, 'r') as f:
        return json.load(f)

def generate_report(analysis):
    report = f"Total titles found: {analysis['total_titles']}\n"
    report += "\n".join(analysis['titles'])
    return report

# Exemple d’usage
if __name__ == "__main__":
    url = "https://example.com"
    raw_html = fetch_data(url)
    data = process_data(raw_html)
    analysis = generate_analysis(data)
    save_analysis(analysis)
    print(generate_report(analysis))

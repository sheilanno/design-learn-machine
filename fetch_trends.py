import feedparser
import json
import os
import re
import time
from datetime import datetime
from google import genai
from supabase import create_client

client = genai.Client(api_key=os.environ['GEMINI_API_KEY'])
db = create_client(os.environ['SUPABASE_URL'], os.environ['SUPABASE_KEY'])

FEEDS = [
    {'source': "It's Nice That", 'url': 'https://www.itsnicethat.com/rss'},
    {'source': 'Creative Boom',  'url': 'https://www.creativeboom.com/feed/'},
    {'source': 'Design Week',    'url': 'https://www.designweek.co.uk/feed/'},
    {'source': 'Brand New',      'url': 'https://www.underconsideration.com/brandnew/feed/'},
]

def get_preferences():
    rows = db.table('saved_designs').select('kategori').execute().data
    counts = {}
    for row in rows:
        k = row.get('kategori', '')
        if k:
            counts[k] = counts.get(k, 0) + 1
    return sorted(counts, key=counts.get, reverse=True)[:3]

def extract_image(entry):
    if hasattr(entry, 'media_content') and entry.media_content:
        return entry.media_content[0].get('url', '')
    if hasattr(entry, 'enclosures') and entry.enclosures:
        return entry.enclosures[0].get('href', '')
    content = ''
    if entry.get('content'):
        content = entry.content[0].get('value', '')
    elif entry.get('summary'):
        content = entry.summary
    m = re.search(r'<img[^>]+src=["\']([^"\']+)["\']', content)
    return m.group(1) if m else ''

def fetch_articles():
    articles = []
    for feed in FEEDS:
        try:
            parsed = feedparser.parse(feed['url'])
            count = 0
            for entry in parsed.entries:
                if count >= 3:
                    break
                articles.append({
                    'title': entry.get('title', '').strip(),
                    'link': entry.get('link', ''),
                    'summary': re.sub('<[^>]+>', '', entry.get('summary', ''))[:400],
                    'source': feed['source'],
                    'image': extract_image(entry),
                })
                count += 1
            print(f"  RSS {feed['source']}: {count} artikel")
        except Exception as e:
            print(f"  RSS {feed['source']} gagal: {e}")
    return articles[:10]

def analyze(article, preferences):
    pref_hint = f"Pengguna suka: {', '.join(preferences)}." if preferences else ""
    prompt = f"""Kamu adalah guru desain grafis untuk pemula Indonesia. {pref_hint}

Artikel dari {article['source']}:
Judul: {article['title']}
Ringkasan: {article['summary']}

Tulis analisis dalam Bahasa Indonesia (80-100 kata) yang:
1. Menjelaskan apa yang menarik dari desain ini
2. Mengaitkan dengan SATU teori desain grafis (color theory / tipografi / komposisi / kontras / hierarchy / branding identity)
3. Memberi pelajaran konkret untuk pemula

Balas HANYA dengan JSON ini, tanpa teks lain:
{{
  "penjelasan": "...",
  "kategori": "branding | tipografi | ilustrasi | packaging | poster | color | visual identity",
  "tingkat": "mudah | menengah | lanjut",
  "teori": "nama teori singkat"
}}"""

    response = client.models.generate_content(
        model='gemini-1.5-flash',
        contents=prompt
    )
    text = re.sub(r'```(?:json)?\n?', '', response.text).strip().rstrip('`')
    return json.loads(text)

def main():
    print("Mengambil preferensi pengguna...")
    preferences = get_preferences()
    print(f"Preferensi: {preferences or 'belum ada'}")

    print("\nMengambil artikel dari sumber desain...")
    articles = fetch_articles()
    print(f"Total: {len(articles)} artikel\n")

    trends = []
    for i, article in enumerate(articles):
        try:
            analysis = analyze(article, preferences)
            trends.append({
                'id': f"{datetime.now().strftime('%Y%m%d')}-{i}",
                'title': article['title'],
                'source': article['source'],
                'link': article['link'],
                'image': article['image'],
                'penjelasan': analysis['penjelasan'],
                'kategori': analysis['kategori'],
                'tingkat': analysis['tingkat'],
                'teori': analysis['teori'],
                'date': datetime.now().strftime('%Y-%m-%d'),
            })
            print(f"  ✓ {article['title'][:60]}")
            time.sleep(4)
        except Exception as e:
            print(f"  ✗ {article['title'][:60]} — {e}")
            time.sleep(4)

    if preferences:
        trends.sort(key=lambda t: 0 if t['kategori'] in preferences else 1)

    os.makedirs('data', exist_ok=True)
    with open('data/trends.json', 'w', encoding='utf-8') as f:
        json.dump({
            'date': datetime.now().strftime('%Y-%m-%d'),
            'updated': datetime.now().strftime('%d %B %Y pukul %H:%M WIB'),
            'preferences': preferences,
            'trends': trends
        }, f, ensure_ascii=False, indent=2)

    print(f"\nSelesai! {len(trends)} tren tersimpan.")

if __name__ == '__main__':
    main()

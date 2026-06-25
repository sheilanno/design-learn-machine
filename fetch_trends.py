import feedparser
import json
import os
import re
import random
from datetime import datetime
from supabase import create_client

db = create_client(os.environ['SUPABASE_URL'], os.environ['SUPABASE_KEY'])

FEEDS = [
    {'source': "It's Nice That", 'url': 'https://www.itsnicethat.com/rss'},
    {'source': 'Creative Boom',  'url': 'https://www.creativeboom.com/feed/'},
    {'source': 'Design Week',    'url': 'https://www.designweek.co.uk/feed/'},
    {'source': 'Brand New',      'url': 'https://www.underconsideration.com/brandnew/feed/'},
    {'source': 'Dezeen',         'url': 'https://www.dezeen.com/feed/'},
    {'source': 'Eye on Design',  'url': 'https://eyeondesign.aiga.org/feed/'},
]

TEORI_DESAIN = {
    'branding': [
        {'teori': 'Brand Identity', 'penjelasan': 'Identitas brand yang kuat menggunakan elemen visual yang konsisten — warna, tipografi, dan bentuk yang berulang menciptakan pengenalan instan di benak audiens. Pemula bisa belajar bahwa konsistensi adalah kunci: satu palet warna dan satu keluarga font sudah cukup untuk membangun karakter brand yang kuat.', 'tingkat': 'menengah'},
        {'teori': 'Visual Hierarchy', 'penjelasan': 'Desain branding yang baik mengarahkan mata audiens secara bertahap — dari logo ke tagline ke informasi pendukung. Hierarchy visual ini dicapai lewat perbedaan ukuran, berat font, dan kontras warna. Untuk pemula: selalu tentukan satu elemen utama yang ingin paling dilihat pertama.', 'tingkat': 'mudah'},
        {'teori': 'Color Psychology', 'penjelasan': 'Pemilihan warna dalam branding bukan soal estetika semata, melainkan psikologi. Warna biru memberi kesan kepercayaan, merah membangkitkan urgensi, hijau mengasosiasikan alam dan kesehatan. Pelajaran untuk pemula: pilih warna berdasarkan emosi yang ingin ditanamkan ke audiens, bukan sekadar preferensi pribadi.', 'tingkat': 'mudah'},
    ],
    'tipografi': [
        {'teori': 'Tipografi', 'penjelasan': 'Pemilihan font bukan sekadar soal keindahan — setiap typeface membawa kepribadian tersendiri. Serif terasa klasik dan otoritatif, sans-serif modern dan bersih, display font dramatis dan ekspresif. Pemula perlu berlatih memadukan maksimal dua font: satu untuk judul, satu untuk teks isi, dengan kontras karakter yang jelas.', 'tingkat': 'mudah'},
        {'teori': 'Type Hierarchy', 'penjelasan': 'Hierarki tipografi mengatur apa yang dibaca pertama, kedua, dan seterusnya. Ini dicapai lewat variasi ukuran, berat (bold/regular), dan warna teks. Desainer profesional jarang menggunakan lebih dari tiga level hierarki dalam satu layout. Untuk pemula: coba atur teks dengan hanya tiga ukuran berbeda dan lihat bedanya.', 'tingkat': 'mudah'},
        {'teori': 'Readability & Legibility', 'penjelasan': 'Legibility adalah apakah huruf bisa dibaca, readability adalah apakah teks nyaman dibaca dalam jumlah banyak. Keduanya dipengaruhi oleh ukuran font, line spacing (leading), dan panjang baris. Pelajaran penting: teks isi idealnya 14-16px dengan line height 1.5x ukuran font untuk kenyamanan membaca.', 'tingkat': 'menengah'},
    ],
    'ilustrasi': [
        {'teori': 'Komposisi Visual', 'penjelasan': 'Ilustrasi yang kuat selalu punya titik fokus yang jelas. Mata penonton diarahkan lewat komposisi — pengaturan elemen, arah garis, dan kontras. Rule of thirds adalah panduan klasik: bayangkan kanvas dibagi 9 kotak, letakkan elemen utama di persimpangan garis untuk hasil yang lebih dinamis dibanding di tengah.', 'tingkat': 'mudah'},
        {'teori': 'Color Harmony', 'penjelasan': 'Ilustrasi membutuhkan harmoni warna agar nyaman dipandang. Skema warna analogus (warna yang berdekatan di color wheel) menciptakan kesan tenang dan menyatu, sementara komplementer (warna berseberangan) menciptakan energi dan kontras. Pemula disarankan mulai dengan palet maksimal 3-4 warna untuk menjaga kesatuan visual.', 'tingkat': 'mudah'},
        {'teori': 'Visual Storytelling', 'penjelasan': 'Ilustrasi terbaik bercerita tanpa kata-kata. Ini dicapai lewat ekspresi karakter, gesture, komposisi adegan, dan detail lingkungan yang mendukung narasi. Untuk pemula: sebelum menggambar, tanyakan pada diri sendiri — "apa satu hal yang ingin saya komunikasikan?" Fokus pada satu pesan membuat ilustrasi lebih kuat.', 'tingkat': 'menengah'},
    ],
    'packaging': [
        {'teori': 'Desain Kemasan', 'penjelasan': 'Kemasan yang efektif harus menarik perhatian di rak dalam 3 detik. Ini dicapai lewat kombinasi warna kontras, tipografi besar, dan visual yang langsung mengkomunikasikan isi produk. Pemula bisa belajar bahwa desain kemasan memiliki dua momen: dilihat dari jauh (butuh kontras kuat) dan dipegang (butuh detail dan tekstur).', 'tingkat': 'menengah'},
        {'teori': 'Brand Consistency', 'penjelasan': 'Lini produk yang kuat menggunakan sistem desain yang konsisten — elemen yang berulang seperti warna, font, dan pola, dengan variasi yang cukup untuk membedakan varian. Ini disebut design system. Untuk pemula: perhatikan bagaimana brand besar mempertahankan identitas di seluruh lini produk mereka sebagai studi kasus.', 'tingkat': 'lanjut'},
    ],
    'poster': [
        {'teori': 'Kontras Visual', 'penjelasan': 'Poster yang berhasil mengandalkan kontras — kontras ukuran, warna, berat tipografi, dan tekstur. Kontras yang kuat membuat poster terbaca dari jarak jauh dan dalam waktu singkat. Prinsip sederhana untuk pemula: pastikan selalu ada satu elemen yang jauh lebih dominan dari elemen lainnya dalam setiap desain poster.', 'tingkat': 'mudah'},
        {'teori': 'Grid System', 'penjelasan': 'Di balik poster yang terlihat bebas dan artistik, hampir selalu ada sistem grid yang tidak terlihat. Grid membantu menyelaraskan elemen secara konsisten dan menciptakan ritme visual. Pemula dapat mulai berlatih dengan grid sederhana 4 atau 6 kolom sebelum bereksperimen dengan layout yang lebih kompleks.', 'tingkat': 'menengah'},
    ],
    'color': [
        {'teori': 'Color Theory', 'penjelasan': 'Color theory adalah ilmu di balik kombinasi warna yang harmonis. Tiga skema dasar: monokromatik (variasi satu warna), analogus (warna bersebelahan di color wheel), dan komplementer (warna berhadapan). Untuk pemula, mulailah dengan monokromatik karena paling mudah menghasilkan tampilan yang kohesif dan profesional.', 'tingkat': 'mudah'},
        {'teori': 'Color Contrast', 'penjelasan': 'Kontras warna menentukan keterbacaan dan hierarki visual. WCAG (standar aksesibilitas web) mensyaratkan rasio kontras minimum 4.5:1 antara teks dan latar belakang. Alat seperti Coolors atau Adobe Color bisa membantu mengecek kontras. Pelajaran untuk pemula: warna terang di atas gelap selalu lebih mudah dibaca daripada warna senada.', 'tingkat': 'mudah'},
    ],
    'visual identity': [
        {'teori': 'Visual Identity System', 'penjelasan': 'Identitas visual yang kuat adalah sistem, bukan sekadar logo. Sistem ini mencakup palet warna, tipografi, pola, ikonografi, dan gaya fotografi yang bekerja bersama secara konsisten. Pemula sering fokus hanya pada logo, padahal logo hanyalah satu elemen kecil dari ekosistem visual brand yang lebih besar.', 'tingkat': 'lanjut'},
        {'teori': 'Logo Design', 'penjelasan': 'Logo yang baik harus bekerja dalam berbagai ukuran dan konteks — dari favicon kecil di browser hingga billboard besar. Ini berarti logo harus sederhana, mudah diingat, dan efektif dalam satu warna sekalipun. Pemula bisa berlatih menguji desain logo dalam ukuran 16px × 16px: jika masih terbaca, desainnya cukup kuat.', 'tingkat': 'menengah'},
    ],
}

KATA_KUNCI_KATEGORI = {
    'branding': ['brand', 'identity', 'logo', 'rebrand', 'corporate'],
    'tipografi': ['type', 'font', 'typography', 'typeface', 'lettering', 'script'],
    'ilustrasi': ['illustrat', 'drawing', 'artwork', 'paint', 'artist', 'sketch'],
    'packaging': ['packag', 'label', 'product design', 'bottle', 'box'],
    'poster': ['poster', 'campaign', 'print', 'editorial', 'publication'],
    'color': ['colour', 'color', 'palette', 'pigment', 'chromatic'],
    'visual identity': ['visual identity', 'identity system', 'brand system', 'design system'],
}

def get_preferences():
    rows = db.table('saved_designs').select('kategori').execute().data
    counts = {}
    for row in rows:
        k = row.get('kategori', '')
        if k:
            counts[k] = counts.get(k, 0) + 1
    return sorted(counts, key=counts.get, reverse=True)[:3]

def detect_category(title, summary):
    text = (title + ' ' + summary).lower()
    for kategori, keywords in KATA_KUNCI_KATEGORI.items():
        if any(kw in text for kw in keywords):
            return kategori
    return random.choice(list(TEORI_DESAIN.keys()))

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
                if count >= 2:
                    break
                title = entry.get('title', '').strip()
                if not title:
                    continue
                articles.append({
                    'title': title,
                    'link': entry.get('link', ''),
                    'summary': re.sub('<[^>]+>', '', entry.get('summary', ''))[:300],
                    'source': feed['source'],
                    'image': extract_image(entry),
                })
                count += 1
            print(f"  RSS {feed['source']}: {count} artikel")
        except Exception as e:
            print(f"  RSS {feed['source']} gagal: {e}")
    return articles[:10]

def main():
    print("Mengambil preferensi pengguna...")
    preferences = get_preferences()
    print(f"Preferensi: {preferences or 'belum ada'}")

    print("\nMengambil artikel dari sumber desain...")
    articles = fetch_articles()
    print(f"Total: {len(articles)} artikel\n")

    trends = []
    used_tips = {k: [] for k in TEORI_DESAIN}

    for i, article in enumerate(articles):
        kategori = detect_category(article['title'], article['summary'])
        tips = TEORI_DESAIN[kategori]
        available = [t for t in tips if t not in used_tips[kategori]]
        if not available:
            used_tips[kategori] = []
            available = tips
        tip = random.choice(available)
        used_tips[kategori].append(tip)

        trends.append({
            'id': f"{datetime.now().strftime('%Y%m%d')}-{i}",
            'title': article['title'],
            'source': article['source'],
            'link': article['link'],
            'image': article['image'],
            'penjelasan': tip['penjelasan'],
            'kategori': kategori,
            'tingkat': tip['tingkat'],
            'teori': tip['teori'],
            'date': datetime.now().strftime('%Y-%m-%d'),
        })
        print(f"  ✓ {article['title'][:60]} [{kategori}]")

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

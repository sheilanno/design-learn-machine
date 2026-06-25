"""
DesignRef - pengambil & penganalisa desain harian.
Sumber: Unsplash, Pexels, Pixabay (pakai key) + Openverse (tanpa key).
Analisa: warna dominan (Pillow) + AI berlapis (Gemini -> Groq -> template).
"""
import os
import io
import re
import json
import time
import base64
import random
import colorsys
from datetime import datetime, timezone, timedelta

import requests
from PIL import Image

WIB = timezone(timedelta(hours=7))

UNSPLASH_KEY = os.environ.get("UNSPLASH_KEY", "")
PEXELS_KEY = os.environ.get("PEXELS_KEY", "")
PIXABAY_KEY = os.environ.get("PIXABAY_KEY", "")
GEMINI_KEY = os.environ.get("GEMINI_API_KEY", "")
GROQ_KEY = os.environ.get("GROQ_API_KEY", "")

ARCHIVE_PATH = "data/designs.json"
PER_CAT = 6  # jumlah karya per kategori (5 kategori x 6 = 30/hari)

# 5 kategori: query pencarian, apakah foto, dan aspek analisa yang sesuai
CATEGORIES = {
    "katalog": {
        "queries": [
            "fashion lookbook editorial minimal photography",
            "fashion ecommerce product grid clean",
            "streetwear lookbook editorial campaign",
            "fashion brand editorial campaign lookbook",
            "food menu design cafe restaurant",
            "food product photography flat lay",
            "furniture catalog interior lifestyle",
            "product still life minimal studio",
            "beauty cosmetics product catalog",
            "jewelry accessories product photography",
            "magazine editorial fashion spread",
            "grocery product packaging flat lay",
        ],
        "photo": False,
        "aspects": [
            ("FONT", "baca teks yang benar-benar ada di katalog ini. Kenapa font itu (serif/sans/display) dipilih buat nama brand, dan kenapa font yang sama/beda dipakai buat nama produk & harga/detail? Hubungkan karakter font itu sama kesan brand yang ditampilkan"),
            ("WARNA", "warna dominan & pendukung di katalog ini, hubungan keduanya, dan gimana warna itu bikin produk makin 'kejual' atau memperkuat identitas brand-nya"),
            ("LAYOUT", "sistem susunannya: foto full-bleed, grid banyak produk, atau split foto-teks? Lihat pemakaian ruang kosong, jarak antar item, konsistensi grid, dan urutan mata kamu pas menjelajahi halaman ini"),
        ],
    },
    "poster": {
        "queries": [
            "concert gig poster",
            "exhibition poster typography",
            "movie poster graphic",
            "typographic poster design",
            "swiss graphic design poster",
            "music poster art",
            "film noir movie poster",
            "vintage travel poster",
            "jazz concert poster",
            "art exhibition poster minimal",
            "theatre performance poster",
            "band tour poster",
        ],
        "photo": False,
        "openverse_first": True,  # Openverse punya poster ASLI (gig/exhibition/movie) — match referensi
        "aspects": [
            ("FONT", "baca headline & teks yang ada di poster ini. Kenapa font ITU (display tebal/serif/condensed) dipilih buat kata utama, dan gimana karakternya nyambung sama pesan/acara/brand yang dipromosikan?"),
            ("WARNA", "warna dominan & pendukung di poster ini, hubungan keduanya (kontras/senada), dan mood yang dibangun — gimana warna itu narik perhatian bahkan dari jarak jauh"),
            ("LAYOUT", "titik fokus utama (mata jatuh ke mana duluan?), hierarki ukuran teks, dan pemakaian ruang kosong. Komposisinya simetris kalem atau asimetris berani?"),
        ],
    },
    "UI/UX": {
        "queries": [
            "saas landing page web design",
            "mobile app interface onboarding",
            "web dashboard analytics ui",
            "portfolio website minimal",
            "ecommerce product page ui",
            "agency studio website bold typography",
            "fintech app ui design",
            "startup landing page hero",
        ],
        "photo": False,
        "feed": "onepagelove",
        "aspects": [
            ("LAYOUT", "susunan komponen & seksi halaman ini: grid, navigasi, urutan blok dari atas ke bawah. Gimana whitespace dipakai biar napas & gak sesak?"),
            ("FONT", "baca teks di UI ini. Kenapa font ITU dipilih buat headline/hero vs teks body, dan gimana karakternya mencerminkan kepribadian brand/produknya?"),
            ("WARNA", "warna utama, warna aksen buat tombol/CTA, kontras teks vs background, dan mood yang dibangun. Kontrasnya cukup biar nyaman dibaca?"),
            ("USABILITY", "kejelasan: aksi utama (CTA) gampang ketemu? Hierarki jelas pengguna harus ngapain duluan? Alurnya gampang ditebak atau bikin bingung?"),
        ],
    },
    "digital imaging": {
        "queries": [
            "photo collage mixed media graphic design editorial",
            "creative photography graphic overlay mixed media",
            "surreal product photography creative composition",
            "photo manipulation halftone duotone graphic design",
            "photo typography editorial poster mixed media",
            "digital art photo illustration creative editorial",
            "pop art portrait bold graphic",
            "double exposure photography art",
            "risograph print poster design",
            "cutout paper collage poster",
            "glitch art experimental photography",
            "y2k graphic design collage",
        ],
        "photo": False,
        "aspects": [
            ("TEKNIK", "teknik pengolahan yang KELIHATAN di gambar ini — halftone (titik-titik), duotone (2 warna), color pop, kolase/cutout, pikselasi, blur/distorsi, atau grafis yang ditumpuk di atas foto. Sebut tekniknya dengan spesifik + efek rasa yang dihasilkan"),
            ("WARNA", "color grading/treatment-nya (misal duotone pink, monokrom, saturasi tinggi) + warna utama & pendukung + mood yang kebangun dari perlakuan warna ini"),
            ("FONT", "baca kata/kalimat yang ada di gambar. Kenapa font ITU dipilih buat kata ITU, dan gimana hubungannya sama pesan/brand/konsep yang mau ditonjolkan"),
            ("KOMPOSISI", "gimana foto, teks, & elemen grafis ditata bareng — apa teks sengaja nimpa foto/subjek? Mana titik fokusnya? Seimbang atau sengaja 'berantakan' demi kesan editorial? Ke mana mata jatuh duluan"),
        ],
    },
    "photography": {
        "queries": [
            "35mm film photography portrait",
            "analog film street photography",
            "candid lifestyle photography friends",
            "night street photography neon city",
            "film photography couple candid",
            "documentary everyday life photography",
            "golden hour film portrait",
            "japanese street photography film",
            "grainy film aesthetic snapshot",
            "flash photography night party",
            "summer film photography youth",
            "melancholic cinematic portrait",
        ],
        "photo": True,
        "aspects": [
            ("ANGLE", "sudut & jarak pengambilan foto ini — low angle (dari bawah, kesan gagah), eye-level (akrab), atau high angle (dari atas, kesan kecil)? Jarak deket (intim) atau jauh (lapang)? Apa efeknya ke subjek?"),
            ("CAHAYA", "sumber & arah cahaya di foto ini — natural/matahari atau buatan (neon/lampu kota)? Dari depan, samping, atau belakang (backlight)? Keras-kontras atau lembut-merata? Gimana cahaya itu bentuk mood-nya?"),
            ("WARNA", "warna dominan & suhu warnanya (hangat/sejuk) + apakah ada kesan 'film/analog' (warna agak pudar, ada grain, tone nostalgia)? Gimana palet itu bangun suasana foto?"),
            ("KOMPOSISI", "framing-nya — rule of thirds, leading lines, simetri, atau candid/spontan yang sengaja gak rapi? Ke mana mata diarahkan & gimana ruang di sekitar subjek dipakai?"),
            ("MOMEN", "ini momen candid/spontan atau ditata? Apa cerita/perasaan yang kerasa — kenapa momen 'biasa' ini jadi menarik buat dibekukan? Hubungin sama kesan sinematik/film kalau ada"),
        ],
    },
}


# ---------- util warna ----------

def quantize_palette(img, n=4):
    small = img.convert("RGB").resize((100, 100))
    result = small.quantize(colors=n, method=Image.FASTOCTREE)
    pal = result.getpalette()
    counts = sorted(result.getcolors(), reverse=True)
    colors = []
    for count, idx in counts[:n]:
        r, g, b = pal[idx * 3:idx * 3 + 3]
        colors.append(((r, g, b), count))
    return colors


def hex_of(rgb):
    return "#%02X%02X%02X" % rgb


def color_mood(rgb):
    r, g, b = [x / 255.0 for x in rgb]
    h, s, v = colorsys.rgb_to_hsv(r, g, b)
    if s < 0.12:
        if v > 0.8:
            return "putih/krem", "bersih, minimalis, lapang"
        if v < 0.25:
            return "hitam", "dramatis, premium, serius"
        return "abu-abu", "tenang, seimbang, elegan"
    deg = h * 360
    if deg < 20 or deg >= 330:
        return "merah", "berani, energik, penuh gairah"
    if deg < 45:
        return "oranye", "hangat, ramah, antusias"
    if deg < 70:
        return "kuning", "ceria, optimis, penuh energi"
    if deg < 160:
        return "hijau", "segar, alami, menenangkan"
    if deg < 200:
        return "toska", "sejuk, modern, menyegarkan"
    if deg < 250:
        return "biru", "tenang, terpercaya, kadang melankolis/sedih"
    if deg < 290:
        return "ungu", "kreatif, mewah, misterius"
    return "pink/magenta", "playful, lembut, berani"


def hue_deg(rgb):
    r, g, b = [x / 255.0 for x in rgb]
    h, s, v = colorsys.rgb_to_hsv(r, g, b)
    return h * 360, s, v


def color_combo(pal_rgb):
    """Jelaskan hubungan warna utama & sekunder secara rinci."""
    c1 = pal_rgb[0]
    n1, k1 = color_mood(c1)
    h1, s1, v1 = hue_deg(c1)
    if len(pal_rgb) < 2:
        return f"Warna utamanya {n1} — memberi kesan {k1}."
    c2 = pal_rgb[1]
    n2, k2 = color_mood(c2)
    h2, s2, v2 = hue_deg(c2)
    diff = abs(h1 - h2)
    diff = min(diff, 360 - diff)

    if s1 < 0.12 and s2 < 0.12:
        rel = (f"Keduanya warna netral ({n1} & {n2}) — masuk satu palet monokrom, "
               f"jadi kesannya minimalis, elegan, dan tidak ramai.")
    elif s2 < 0.12:
        rel = (f"Dipasangkan dengan warna netral {n2} — kombinasi warna + netral ini "
               f"bikin {n1} makin menonjol, hasilnya bersih dan tidak berantakan.")
    elif n1 == n2:
        rel = (f"Sekundernya juga {n2} tapi beda gelap-terang — ini skema monokromatik "
               f"(satu warna saja), aman & rapi untuk pemula.")
    elif diff < 30:
        rel = (f"Warna sekundernya {n2}, masih satu keluarga dengan {n1} (analogus/senada) — "
               f"transisinya halus, enak dipandang, terasa harmonis.")
    elif 150 <= diff <= 210:
        rel = (f"Sekundernya {n2} yang berseberangan dengan {n1} (komplementer) — "
               f"kontras kuat ini bikin desain 'pop' dan berani.")
    else:
        rel = (f"Dipadukan {n1} dengan {n2} — kontras sedang yang memberi variasi "
               f"tanpa saling tabrakan.")
    return f"Warna utama {n1} (kesan: {k1}). {rel}"


def temperature(rgb):
    r, g, b = rgb
    if abs(r - b) < 18:
        return "netral"
    return "hangat" if r > b else "sejuk"


def analyze_colors(img):
    pal = quantize_palette(img, 4)
    rgbs = [c for c, _ in pal]
    hexes = [hex_of(c) for c in rgbs]
    dom = rgbs[0]
    nama, kesan = color_mood(dom)
    sek = color_mood(rgbs[1])[0] if len(rgbs) > 1 else ""
    suhu = temperature(dom)
    return {
        "palette": hexes,
        "dominan_nama": nama,
        "sekunder_nama": sek,
        "dominan_kesan": kesan,
        "suhu": suhu,
        "combo": color_combo(rgbs),
    }


# ---------- sumber gambar ----------

def fetch_unsplash(query, n=3):
    if not UNSPLASH_KEY:
        return []
    try:
        r = requests.get(
            "https://api.unsplash.com/search/photos",
            params={"query": query, "per_page": n, "orientation": "landscape"},
            headers={"Authorization": f"Client-ID {UNSPLASH_KEY}"},
            timeout=20,
        )
        r.raise_for_status()
        out = []
        for it in r.json().get("results", []):
            out.append({
                "title": (it.get("description") or it.get("alt_description") or query).strip()[:90],
                "image": it["urls"]["regular"],
                "link": it["links"]["html"],
                "source": "Unsplash",
                "author": it["user"]["name"],
            })
        return out
    except Exception as e:
        print(f"    Unsplash '{query}' gagal: {e}")
        return []


def fetch_pexels(query, n=3):
    if not PEXELS_KEY:
        return []
    try:
        r = requests.get(
            "https://api.pexels.com/v1/search",
            params={"query": query, "per_page": n, "orientation": "landscape"},
            headers={"Authorization": PEXELS_KEY},
            timeout=20,
        )
        r.raise_for_status()
        out = []
        for it in r.json().get("photos", []):
            out.append({
                "title": (it.get("alt") or query).strip()[:90],
                "image": it["src"]["large"],
                "link": it["url"],
                "source": "Pexels",
                "author": it.get("photographer", ""),
            })
        return out
    except Exception as e:
        print(f"    Pexels '{query}' gagal: {e}")
        return []


def fetch_pixabay(query, n=3):
    if not PIXABAY_KEY:
        return []
    try:
        r = requests.get(
            "https://pixabay.com/api/",
            params={"key": PIXABAY_KEY, "q": query, "per_page": max(n, 3),
                    "image_type": "all", "safesearch": "true"},
            timeout=20,
        )
        r.raise_for_status()
        out = []
        for it in r.json().get("hits", [])[:n]:
            out.append({
                "title": (it.get("tags") or query).strip()[:90],
                "image": it["largeImageURL"],
                "link": it["pageURL"],
                "source": "Pixabay",
                "author": it.get("user", ""),
            })
        return out
    except Exception as e:
        print(f"    Pixabay '{query}' gagal: {e}")
        return []


def fetch_openverse(query, n=3):
    try:
        r = requests.get(
            "https://api.openverse.org/v1/images/",
            params={"q": query, "page_size": n, "license_type": "all"},
            timeout=20,
        )
        r.raise_for_status()
        out = []
        for it in r.json().get("results", []):
            img = it.get("url")
            if not img:
                continue
            out.append({
                "title": (it.get("title") or query).strip()[:90],
                "image": img,
                "link": it.get("foreign_landing_url") or img,
                "source": "Openverse",
                "author": it.get("creator", "") or "",
            })
        return out
    except Exception as e:
        print(f"    Openverse '{query}' gagal: {e}")
        return []


def fetch_onepagelove(n=12):
    """Galeri kurasi landing page / web UI — pas untuk kategori UI/UX."""
    try:
        r = requests.get("https://onepagelove.com/feed",
                         headers={"User-Agent": "Mozilla/5.0"}, timeout=20)
        r.raise_for_status()
        items = re.findall(r"<item>(.*?)</item>", r.text, re.DOTALL)
        out = []
        for it in items:
            img = re.search(r"https?://assets\.onepagelove\.com[^\s\"'<>\]]+?\.(?:jpg|jpeg|png|webp)", it)
            if not img:
                continue
            title = re.search(r"<title>(.*?)</title>", it, re.DOTALL)
            link = re.search(r"<link>(.*?)</link>", it, re.DOTALL)
            t = (title.group(1) if title else "Web UI design").strip()
            t = re.sub(r"^Website Inspiration:\s*", "", t)[:90]
            out.append({
                "title": t,
                "image": img.group(0),
                "link": link.group(1).strip() if link else img.group(0),
                "source": "One Page Love",
                "author": "",
            })
        return out[:n]
    except Exception as e:
        print(f"    One Page Love gagal: {e}")
        return []


def collect(query, info):
    pool = []
    # poster: Openverse punya poster asli (gig/exhibition/movie) -> jadikan utama.
    # Openverse dicoba dulu; kalau gambarnya (CDN Flickr) gagal/kena rate-limit,
    # proses lanjut otomatis ke stock di ekor list ini (poster tak pernah kosong).
    if info.get("openverse_first"):
        pool += fetch_openverse(query, 6)
        pool += fetch_unsplash(query, 2)
        pool += fetch_pexels(query, 2)
        return pool
    if info["photo"]:
        pool += fetch_unsplash(query, 3)
        pool += fetch_openverse(query, 2)
    else:
        pool += fetch_unsplash(query, 2)
        pool += fetch_pexels(query, 2)
        pool += fetch_pixabay(query, 2)
        if not pool:
            pool += fetch_openverse(query, 3)
    return pool


# ---------- AI analisa ----------

CAT_CONTEXT = {
    "katalog": (
        "Katalog = showcase produk yang tersusun rapi: bisa fashion lookbook (model + outfit "
        "lengkap dengan nama item & harga), menu makanan/minuman, katalog furniture, lifestyle "
        "product catalog, atau editorial brand campaign. Ciri khasnya: foto produk yang bersih, "
        "hierarki teks konsisten (nama brand -> nama produk -> detail/harga), dan grid teratur "
        "yang enak dijelajahi mata."
    ),
    "poster": (
        "Poster = satu bidang yang harus 'menangkap' mata dalam sekejap, sering dari jarak jauh. "
        "Bisa event poster, typographic poster (tipografi jadi bintang utama), atau campaign poster. "
        "Ciri khasnya: satu titik fokus dominan, hierarki teks tegas (headline gede banget -> info "
        "pendukung -> detail kecil), dan keberanian main ruang kosong serta skala."
    ),
    "UI/UX": (
        "UI/UX = desain interface digital yang harus enak dilihat SEKALIGUS enak dipakai. Biasanya "
        "landing page, mobile app, web dashboard, atau SaaS. Ciri khas yang bagus: hero section "
        "dengan headline tipografi yang berani, navigasi jelas, satu tombol aksi (CTA) yang menonjol, "
        "warna aksen konsisten, dan banyak ruang napas (whitespace)."
    ),
    "digital imaging": (
        "Digital imaging = foto yang 'diolah' jadi karya grafis, bukan foto polos. Ciri khasnya: "
        "foto dipadukan dengan tipografi besar dan teknik seperti halftone (titik-titik), duotone "
        "(2 warna), color pop, kolase/cutout, pikselasi, atau bentuk grafis yang ditempel di atas "
        "foto. Foto diperlakukan sebagai 'bahan' desain, sering sengaja bertabrakan dengan teks "
        "demi kesan editorial yang bold."
    ),
    "photography": (
        "Foto bergaya film/analog & candid — portrait, street (sering urban/Tokyo malam dengan neon), "
        "lifestyle anak muda, pasangan/teman, atau momen sehari-hari yang 'biasa' tapi jadi indah "
        "(misal kresek isi jeruk di lantai, rebahan di rumput). Ciri khasnya: kesan grain film, warna "
        "natural/nostalgia, momen spontan & sinematik. Analisa kenapa foto ini 'kena' & berasa hidup, "
        "bukan cuma deskripsi isinya."
    ),
}


def build_prompt(cat, info, combo, suhu):
    role = ("fotografer yang asik ngajarin temennya" if info["photo"]
            else "desainer yang asik ngajarin temennya")
    ctx = CAT_CONTEXT.get(cat, "")
    bd_items = ",\n    ".join(
        '{"label": "%s", "text": "JELASKAN soal %s yang KAMU LIHAT DI GAMBAR INI. Spesifik ke gambar ini, bukan generik. 2-3 kalimat, santai banget."}' % (lab, hint)
        for lab, hint in info["aspects"]
    )
    return f"""Kamu {role}. Lihat gambar kategori "{cat}" ini. {ctx} Analisa SESUAI yang KAMU LIHAT di gambar ini secara spesifik — jangan generik, jangan template. Gaya bahasa super santai & non-formal, kayak ngobrol sama temen (boleh pakai 'kamu', 'nih', 'banget'), tapi tetap jelas & ada ilmunya.

PENTING — kalau ada aspek FONT: jangan cuma sebut "serifnya bagus". Jelaskan MENGAPA font ITU dipilih untuk kata/kalimat TERTENTU yang kamu lihat (misalnya: "kata 'URBAN' pakai font condensed bold karena..."), dan apa kaitannya dengan brand atau konsep yang mau disampaikan.

Data warna asli dari gambar: {combo} Suhu warna: {suhu}.

Balas HANYA JSON ini (Bahasa Indonesia, tanpa teks lain):
{{
  "judul": "judul singkat & menarik untuk karya ini (spesifik ke isi gambar, bukan cuma nama kategori)",
  "kategori": "{cat}",
  "tingkat": "mudah|menengah|lanjut",
  "teori": "nama 1 teori desain/fotografi yang relevan dengan gambar ini, atau '-'",
  "breakdown": [
    {bd_items}
  ],
  "pelajaran": "1 kalimat pelajaran konkret & santai yang bisa pemula tiru dari gambar ini"
}}"""


def parse_json(text):
    text = re.sub(r"```(?:json)?", "", text).strip().strip("`").strip()
    m = re.search(r"\{.*\}", text, re.DOTALL)
    return json.loads(m.group(0) if m else text)


def ai_gemini(prompt, img_b64):
    if not GEMINI_KEY:
        raise RuntimeError("no gemini key")
    url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.0-flash:generateContent?key={GEMINI_KEY}"
    body = {
        "contents": [{"parts": [
            {"text": prompt},
            {"inline_data": {"mime_type": "image/jpeg", "data": img_b64}},
        ]}],
        "generationConfig": {"temperature": 0.7},
    }
    r = requests.post(url, json=body, timeout=40)
    if r.status_code != 200:
        # jangan pakai raise_for_status (URL-nya bawa key); pakai body errornya saja
        raise RuntimeError(f"HTTP {r.status_code}: {r.text[:160]}")
    data = r.json()
    if not data.get("candidates"):
        raise RuntimeError(f"no candidates: {str(data)[:160]}")
    txt = data["candidates"][0]["content"]["parts"][0]["text"]
    return parse_json(txt)


def ai_groq(prompt, img_b64):
    if not GROQ_KEY:
        raise RuntimeError("no groq key")
    r = requests.post(
        "https://api.groq.com/openai/v1/chat/completions",
        headers={"Authorization": f"Bearer {GROQ_KEY}"},
        json={
            "model": "meta-llama/llama-4-scout-17b-16e-instruct",
            "temperature": 0.7,
            "messages": [{"role": "user", "content": [
                {"type": "text", "text": prompt},
                {"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{img_b64}"}},
            ]}],
        },
        timeout=40,
    )
    if r.status_code != 200:
        raise RuntimeError(f"HTTP {r.status_code}: {r.text[:160]}")
    return parse_json(r.json()["choices"][0]["message"]["content"])


TEMPLATE_TEXT = {
    "FONT": "Pilihan font bukan kebetulan — tiap font punya 'karakter' yang nyambung sama brand-nya. Serif (ada kaki kecilnya) kesan klasik & premium, cocok buat brand yang mau kelihatan established. Sans-serif yang bersih lebih ke modern & accessible. Display/condensed yang dramatis biasanya dipilih buat kata yang paling penting supaya langsung 'grab attention'. Tanya diri sendiri: kalau font-nya diganti jadi yang lain, apakah brand-nya masih berasa sama?",
    "LAYOUT": "Susunan elemennya nentuin mata kamu jalan ke mana duluan. Trik gampangnya: pilih satu elemen yang paling pengen ditonjolin, gedein, terus kasih ruang kosong di sekitarnya biar napas. Sisanya disejajarin rapi pakai grid, dijamin langsung keliatan niat.",
    "USABILITY": "Yang bikin UI enak dipakai itu kejelasan: tombol aksi utama harus paling nonjol, teks gampang kebaca, dan alurnya gampang ditebak. Kalau kamu bingung 'abis ini ngapain', berarti desainnya kurang jelas. Semakin gak mikir buat makainya, semakin bagus.",
    "TEKNIK": "Di digital imaging, kuncinya bikin elemen-elemen yang aslinya beda jadi nyatu mulus — perhatiin pencahayaan, bayangan, sama warnanya harus nyambung. Kalau semua elemen kena 'cahaya yang sama', hasil gabungannya bakal keliatan real, bukan tempelan.",
    "KOMPOSISI": "Lihat ke mana mata kamu jatuh pertama kali — itu titik fokusnya. Karya kuat biasanya naruh subjek di garis sepertiga (rule of thirds), bukan pas tengah, terus pakai garis atau ruang kosong buat ngarahin pandangan kamu.",
    "ANGLE": "Perhatiin diambil dari mana: dari bawah (low angle) bikin subjek keliatan gagah & dominan, sejajar mata kesannya akrab & jujur, dari atas bikin subjek keliatan kecil. Makin deket jaraknya, makin intim & berasa emosinya.",
    "CAHAYA": "Cahaya itu 'nyawa' foto. Cahaya dari samping bikin tekstur & dimensi keluar (wajah jadi berkarakter), dari depan rata bikin bersih tapi flat, dari belakang (backlight) bikin siluet atau rim light yang dramatis. Golden hour (sore) kesannya hangat & lembut; siang terik bikin bayangan keras & kontras tinggi. Lihat arah bayangannya — itu ngasih tau dari mana cahayanya datang.",
    "MOMEN": "Foto yang 'kena' biasanya nangkep momen yang jujur — orang lagi ketawa lepas, ngelamun, atau adegan sehari-hari yang biasa aja tapi pas dibekukan jadi puitis. Tanya: apa yang lagi terjadi di sini, dan kenapa fotografer milih MOMEN ini? Momen candid (gak dibikin-bikin) sering kerasa lebih hidup & relatable daripada pose kaku. Kesan film/grain nambahin rasa nostalgia & nyata.",
}

# Template teks khusus per kategori — ditampilkan kalau AI vision gagal
TEMPLATE_BY_CAT = {
    "katalog": {
        "FONT": "Di katalog yang bagus, tipografinya punya hierarchy yang jelas banget: nama brand paling gede, nama produk medium, deskripsi & detail paling kecil. Font serif (ada kaki kecilnya) kesan premium & editorial — cocok buat fashion lookbook atau katalog lifestyle. Font sans-serif yang clean lebih ke modern & accessible, bagus buat menu makanan atau produk tech. Kuncinya: konsisten dari satu produk ke produk berikutnya.",
        "LAYOUT": "Katalog yang kuat itu punya rhythm — mata kamu 'jalan' dari satu produk ke produk lain dengan enak dan natural. Ada yang pakai hero shot (satu gambar besar + beberapa kecil), ada yang full grid rapi (semua sama besar). Yang penting: kasih whitespace yang cukup di sekitar produk biar gak sesak, dan background-nya bersih biar produknya sendiri yang 'ngomong'.",
    },
    "poster": {
        "FONT": "Di poster, font adalah senjata utama. Serif berat atau display font tebal → langsung bikin orang berhenti. Tapi yang lebih penting: font dipilih karena 'karakternya' cocok sama brand/pesan-nya. Brand musik yang raw & urban pilih condensed bold karena terasa agresif & energik. Brand premium pilih thin serif karena terasa eksklusif. Perhatiin kata mana yang digedein — itu yang brand mau kamu ingat duluan.",
        "LAYOUT": "Poster yang efektif punya satu titik gravitasi — mata langsung tau mau lihat ke mana. Bisa headline yang super gede, bisa gambar tunggal yang kuat. Whitespace bukan 'ruang kosong yang sia-sia', tapi senjata buat bikin elemen utama makin menonjol. Coba bold asimetris: taruh elemen utama di sepertiga layar, sisanya ruang napas.",
    },
    "digital imaging": {
        "TEKNIK": "Di digital imaging, tekniknya bisa macem-macem: halftone (foto jadi titik-titik/dots) buat kesan retro & pop art; duotone (foto cuma pakai 2 warna) buat kesan bold & modern; compositing (gabungin beberapa elemen berbeda) butuh perhatian ke pencahayaan & bayangan biar nyatu; color pop (1 warna dibiarkan, sisanya hitam-putih) buat drama fokus. Yang bikin hasilnya bagus: semua elemen terasa 'satu dunia', bukan tempelan.",
        "FONT": "Font di digital imaging sering jadi elemen desain itu sendiri, bukan cuma label. Condensed bold yang super gede di atas foto → brand yang mau terasa powerful & langsung nendang. Thin italic yang halus → brand yang mau terasa poetic & artistik. Yang penting: perhatiin apakah font-nya 'lawan' fotonya (kontras = drama) atau 'nyatu' sama fotonya (harmoni = elegan) — itu pilihan desain yang disengaja.",
        "KOMPOSISI": "Di digital imaging, komposisi bukan cuma soal foto — tapi soal bagaimana foto, teks, dan elemen grafis bekerja bareng. Foto bisa jadi background penuh, atau cuma sebagian yang 'dipotong' buat dipaduin sama grafis. Teks yang gede bisa tumpang tindih sama wajah/subjek foto (ini disengaja buat kesan editorial yang bold). Tanya: apakah mata kamu jatuh ke foto dulu atau ke teks dulu? Itu nunjukin mana yang mau diutamakan brand-nya.",
    },
    "UI/UX": {
        "FONT": "Di UI, font itu suara brand. Headline sering pakai display/serif berkarakter biar hero section langsung 'ngomong' & punya kepribadian; teks body hampir selalu sans-serif bersih yang gampang kebaca di layar. Yang penting: ukuran headline vs body harus beda jelas (hierarki), dan jangan kebanyakan jenis font — 2 cukup. Font yang konsisten bikin produk terasa 'jadi' & profesional.",
        "LAYOUT": "UI yang enak dipandang biasanya pakai grid rapi + whitespace yang lega. Mata dituntun dari atas (hero/headline) turun ke konten lalu ke tombol aksi. Jangan jejalin semua di satu layar — kasih ruang napas antar seksi biar pengguna gak overwhelmed. Konsistensi jarak (spacing) antar elemen itu yang bikin keliatan rapi & profesional.",
    },
    "photography": {
        "ANGLE": "Angle nentuin gimana kita 'memandang' subjek. Low angle (kamera di bawah, ndongak) bikin subjek keliatan gagah, berkuasa, dominan. Eye-level (sejajar mata) kesannya akrab, jujur, setara. High angle (dari atas, nunduk) bikin subjek keliatan kecil, rentan, atau ngasih konteks lingkungan. Makin deket jarak kameranya, makin intim & berasa emosinya.",
        "CAHAYA": "Cahaya itu 'nyawa' foto. Cahaya dari samping bikin tekstur & dimensi keluar, dari depan rata bikin bersih tapi flat, dari belakang (backlight) bikin siluet atau rim light yang dramatis. Golden hour (sore) hangat & lembut; siang terik bikin bayangan keras & kontras tinggi. Lihat arah bayangan buat tau dari mana cahayanya datang.",
    },
}


def template_analysis(item, colors, cat, info):
    cat_texts = TEMPLATE_BY_CAT.get(cat, {})
    bd = []
    for lab, hint in info["aspects"]:
        if lab == "WARNA":
            text = colors["combo"] + " Soalnya warna itu yang pertama nendang emosi orang yang lihat."
        else:
            text = cat_texts.get(lab) or TEMPLATE_TEXT.get(lab, "Perhatiin bagian " + hint + ".")
        bd.append({"label": lab, "text": text})
    return {
        "judul": item["title"] or f"Pilihan {cat} hari ini",
        "kategori": cat,
        "tingkat": "mudah",
        "teori": "-",
        "breakdown": bd,
        "pelajaran": "Mulai dari satu titik fokus yang jelas, sisanya bikin rapi & senada.",
    }


def analyze(item, img, colors, cat, info):
    prompt = build_prompt(cat, info, colors["combo"], colors["suhu"])
    buf = io.BytesIO()
    img.convert("RGB").resize((512, 512)).save(buf, format="JPEG", quality=80)
    img_b64 = base64.b64encode(buf.getvalue()).decode()
    for name, fn in (("Gemini", ai_gemini), ("Groq", ai_groq)):
        try:
            res = fn(prompt, img_b64)
            res["kategori"] = cat
            res["_ai"] = name
            return res
        except Exception as e:
            print(f"    {name} GAGAL: {str(e)[:200]}")
    print("    -> pakai TEMPLATE (analisa generik, bukan per-gambar)")
    res = template_analysis(item, colors, cat, info)
    res["_ai"] = "template"
    return res


# ---------- arsip ----------

def load_archive():
    try:
        with open(ARCHIVE_PATH, encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return {"updated": "", "items": []}


def build_item(item, img, colors, ai, idx):
    return {
        "id": f"{datetime.now(WIB).strftime('%Y%m%d')}-{idx}",
        "title": ai.get("judul") or item["title"],
        "source": item["source"],
        "author": item.get("author", ""),
        "link": item["link"],
        "image": item["image"],
        "kategori": ai.get("kategori", "poster"),
        "tingkat": ai.get("tingkat", "mudah"),
        "teori": ai.get("teori", "-"),
        "breakdown": ai.get("breakdown", []),
        "pelajaran": ai.get("pelajaran", ""),
        "palette": colors["palette"],
        "suhu": colors["suhu"],
        "ai": ai.get("_ai", "template"),
        "date": datetime.now(WIB).strftime("%Y-%m-%d"),
        "added_at": datetime.now(WIB).isoformat(),
    }


def process(item, idx, cat, info, seen_images):
    if item["image"] in seen_images:
        return None
    try:
        resp = requests.get(item["image"], timeout=25,
                            headers={"User-Agent": "DesignRefBot/1.0"})
        resp.raise_for_status()
        img = Image.open(io.BytesIO(resp.content))
    except Exception as e:
        print(f"    download gagal: {str(e)[:60]}")
        return None
    colors = analyze_colors(img)
    ai = analyze(item, img, colors, cat, info)
    seen_images.add(item["image"])
    print(f"  + [{cat}] {(ai.get('judul') or item['title'])[:48]} (AI:{ai.get('_ai')})")
    return build_item(item, img, colors, ai, idx)


def main():
    archive = load_archive()
    seen = {it["image"] for it in archive["items"]}
    new_items = []
    idx = 0

    for cat, info in CATEGORIES.items():
        print(f"\n=== {cat} (target {PER_CAT}) ===")
        got = 0

        if info.get("feed") == "onepagelove":
            feed_items = fetch_onepagelove(40)
            random.shuffle(feed_items)  # variasi: jangan selalu ambil yang teratas
            for cand in feed_items:
                if got >= PER_CAT:
                    break
                built = process(cand, idx, cat, info, seen)
                if built:
                    new_items.append(built)
                    idx += 1
                    got += 1
                    time.sleep(1)

        if got < PER_CAT:
            queries = list(info["queries"])
            random.shuffle(queries)
            for q in queries:
                if got >= PER_CAT:
                    break
                for cand in collect(q, info):
                    if got >= PER_CAT:
                        break
                    built = process(cand, idx, cat, info, seen)
                    if built:
                        new_items.append(built)
                        idx += 1
                        got += 1
                        time.sleep(1)

    archive["items"] = new_items + archive["items"]
    archive["updated"] = datetime.now(WIB).strftime("%d %B %Y, %H:%M WIB")
    archive["last_count"] = len(new_items)

    os.makedirs("data", exist_ok=True)
    with open(ARCHIVE_PATH, "w", encoding="utf-8") as f:
        json.dump(archive, f, ensure_ascii=False, indent=2)

    print(f"\nSelesai! {len(new_items)} item baru. Total arsip: {len(archive['items'])}.")


if __name__ == "__main__":
    main()

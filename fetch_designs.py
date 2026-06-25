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
TARGET_DESIGN = 25
TARGET_PHOTO = 5

# kategori desain grafis + kata kunci pencarian
DESIGN_QUERIES = {
    "branding": ["brand identity design", "logo branding"],
    "tipografi": ["typography poster", "typographic design"],
    "ilustrasi": ["graphic illustration art", "editorial illustration"],
    "packaging": ["packaging design", "product packaging"],
    "poster": ["graphic design poster", "exhibition poster"],
    "color": ["colorful graphic design", "color palette design"],
    "visual identity": ["visual identity brand", "brand guidelines design"],
}
PHOTO_QUERIES = ["cinematic photography", "portrait photography", "street photography",
                 "moody photography", "landscape photography"]


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


def collect(query, is_photo=False):
    pool = []
    if is_photo:
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

PROMPT_DESIGN = """Kamu guru desain grafis yang asik buat pemula. Gaya bahasa santai, non-formal, tapi jelas (boleh pakai 'kamu'). Lihat gambar desain ini.

Data warna terdeteksi: {combo} Suhu warna: {suhu}.

Balas HANYA JSON ini (Bahasa Indonesia, tanpa teks lain):
{{
  "judul": "judul singkat menarik untuk karya ini",
  "kategori": "branding|tipografi|ilustrasi|packaging|poster|color|visual identity",
  "tingkat": "mudah|menengah|lanjut",
  "teori": "nama 1 teori desain yang relevan",
  "breakdown": [
    {{"label": "FONT", "text": "RINCI: jenis hurufnya (serif/sans-serif/script/display), kesan yang dibawa, ketebalan & spasi, dan kenapa cocok. 2-3 kalimat."}},
    {{"label": "WARNA", "text": "RINCI: sebutkan warna utama & sekunder, jelaskan hubungannya (senada/komplementer/monokrom & masih satu palet atau tidak), lalu efek emosinya. 2-3 kalimat."}},
    {{"label": "LAYOUT", "text": "RINCI: susunan elemen, mana titik fokus & hierarchy-nya, pakai grid/simetris/asimetris, peran ruang kosong. 2-3 kalimat."}}
  ],
  "pelajaran": "1 kalimat pelajaran konkret yang bisa pemula tiru"
}}"""

PROMPT_PHOTO = """Kamu fotografer yang asik ngajarin pemula. Gaya bahasa santai, non-formal, tapi jelas. Lihat foto ini.

Data warna terdeteksi: {combo} Suhu warna: {suhu}.

Balas HANYA JSON ini (Bahasa Indonesia, tanpa teks lain):
{{
  "judul": "judul singkat menarik untuk foto ini",
  "kategori": "fotografi",
  "tingkat": "mudah|menengah|lanjut",
  "teori": "nama 1 teori fotografi relevan (rule of thirds, leading lines, dll) atau '-'",
  "breakdown": [
    {{"label": "ANGLE", "text": "RINCI: sudut pengambilan (low/high/eye level), jarak (close-up/wide), efeknya ke kesan subjek. 2-3 kalimat."}},
    {{"label": "WARNA", "text": "RINCI: sebutkan warna utama & sekunder, hubungannya (senada/komplementer/monokrom), lalu mood-nya (cth: biru+hitam = tenang & melankolis). 2-3 kalimat."}},
    {{"label": "KOMPOSISI", "text": "RINCI: penempatan subjek, rule of thirds/leading lines/framing, peran latar & ruang kosong. 2-3 kalimat."}}
  ],
  "pelajaran": "1 kalimat pelajaran konkret buat pemula"
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
    r.raise_for_status()
    txt = r.json()["candidates"][0]["content"]["parts"][0]["text"]
    return parse_json(txt)


def ai_groq(prompt, img_b64):
    if not GROQ_KEY:
        raise RuntimeError("no groq key")
    r = requests.post(
        "https://api.groq.com/openai/v1/chat/completions",
        headers={"Authorization": f"Bearer {GROQ_KEY}"},
        json={
            "model": "llama-3.2-11b-vision-preview",
            "temperature": 0.7,
            "messages": [{"role": "user", "content": [
                {"type": "text", "text": prompt},
                {"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{img_b64}"}},
            ]}],
        },
        timeout=40,
    )
    r.raise_for_status()
    return parse_json(r.json()["choices"][0]["message"]["content"])


def template_analysis(item, colors, is_photo):
    combo = colors["combo"]
    if is_photo:
        return {
            "judul": item["title"] or "Foto pilihan hari ini",
            "kategori": "fotografi",
            "tingkat": "mudah",
            "teori": "warna & mood",
            "breakdown": [
                {"label": "ANGLE", "text": "Perhatikan dari mana foto diambil: sudut rendah (low angle) bikin subjek terasa megah & dominan, sejajar mata terasa akrab & jujur, sudut tinggi bikin subjek terasa kecil. Jarak ambil juga penting — makin dekat makin intim & emosional."},
                {"label": "WARNA", "text": combo + " Warna adalah pembawa emosi utama dalam foto — atur lewat pencahayaan & waktu pengambilan."},
                {"label": "KOMPOSISI", "text": "Lihat ke mana matamu jatuh pertama kali — itu titik fokusnya. Foto kuat biasanya menaruh subjek di garis sepertiga (rule of thirds), bukan pas tengah, dan memanfaatkan garis/ruang kosong untuk mengarahkan pandangan."},
            ],
            "pelajaran": "Sebelum memotret, tanya: 'apa satu hal yang mau aku tonjolkan?'",
        }
    return {
        "judul": item["title"] or "Desain pilihan hari ini",
        "kategori": random.choice(list(DESIGN_QUERIES.keys())),
        "tingkat": "mudah",
        "teori": "color & hierarchy",
        "breakdown": [
            {"label": "FONT", "text": "Pilihan huruf membawa kepribadian: serif (ada 'kaki') terasa klasik & terpercaya, sans-serif terasa modern & bersih, script terasa personal. Perhatikan ketebalan (berat) dan jarak antar huruf — makin lega makin elegan. Aman untuk pemula: cukup padukan maksimal 2 jenis font."},
            {"label": "WARNA", "text": combo + " Pilih warna berdasarkan emosi yang mau ditanam, bukan asal suka."},
            {"label": "LAYOUT", "text": "Susunan elemen menentukan urutan baca. Tentukan satu elemen yang paling mau dilihat duluan lalu besarkan (itu hierarchy), sejajarkan elemen lain pada grid biar rapi, dan sisakan ruang kosong di sekitarnya supaya tidak sesak dan mata bisa 'bernapas'."},
        ],
        "pelajaran": "Konsistensi + satu titik fokus = desain langsung kelihatan rapi.",
    }


def analyze(item, img, colors, is_photo):
    base = PROMPT_PHOTO if is_photo else PROMPT_DESIGN
    prompt = base.format(combo=colors["combo"], suhu=colors["suhu"])
    buf = io.BytesIO()
    img.convert("RGB").resize((512, 512)).save(buf, format="JPEG", quality=80)
    img_b64 = base64.b64encode(buf.getvalue()).decode()
    for name, fn in (("Gemini", ai_gemini), ("Groq", ai_groq)):
        try:
            res = fn(prompt, img_b64)
            res["_ai"] = name
            return res
        except Exception as e:
            print(f"    {name} gagal: {str(e)[:80]}")
    res = template_analysis(item, colors, is_photo)
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


def process(item, idx, is_photo, seen_images):
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
    ai = analyze(item, img, colors, is_photo)
    seen_images.add(item["image"])
    print(f"  + [{ai.get('kategori','?')}] {(ai.get('judul') or item['title'])[:50]} (AI:{ai.get('_ai')})")
    return build_item(item, img, colors, ai, idx)


def main():
    archive = load_archive()
    seen = {it["image"] for it in archive["items"]}
    new_items = []
    idx = 0

    print("=== DESAIN GRAFIS (target %d) ===" % TARGET_DESIGN)
    queries = []
    for kat, qs in DESIGN_QUERIES.items():
        for q in qs:
            queries.append(q)
    random.shuffle(queries)
    for q in queries:
        if len([x for x in new_items if x["kategori"] != "fotografi"]) >= TARGET_DESIGN:
            break
        for cand in collect(q, is_photo=False):
            built = process(cand, idx, False, seen)
            if built:
                new_items.append(built)
                idx += 1
            if len([x for x in new_items if x["kategori"] != "fotografi"]) >= TARGET_DESIGN:
                break
            time.sleep(1)

    print("\n=== FOTOGRAFI (target %d) ===" % TARGET_PHOTO)
    random.shuffle(PHOTO_QUERIES)
    for q in PHOTO_QUERIES:
        if len([x for x in new_items if x["kategori"] == "fotografi"]) >= TARGET_PHOTO:
            break
        for cand in collect(q, is_photo=True):
            built = process(cand, idx, True, seen)
            if built:
                built["kategori"] = "fotografi"
                new_items.append(built)
                idx += 1
            if len([x for x in new_items if x["kategori"] == "fotografi"]) >= TARGET_PHOTO:
                break
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

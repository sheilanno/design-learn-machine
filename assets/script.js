const { createClient } = supabase;
const sb = createClient(SUPABASE_URL, SUPABASE_KEY);

let allTrends = [];
let savedIds = new Set();
let activeFilter = 'semua';

const CAT_ICONS = {
  branding: '◈', tipografi: 'Aa', ilustrasi: '✦',
  packaging: '⬡', poster: '▣', color: '◉', 'visual identity': '◎'
};

async function init() {
  await loadSavedIds();
  if (PAGE === 'index') {
    await loadTrends();
    setupFilters();
  } else {
    await loadSavedPage();
  }
  updateSavedBadge();
}

async function loadSavedIds() {
  const { data } = await sb.from('saved_designs').select('id');
  savedIds = new Set((data || []).map(r => r.id));
}

async function loadTrends() {
  try {
    const res = await fetch('data/trends.json?t=' + Date.now());
    const json = await res.json();
    allTrends = json.trends || [];

    document.getElementById('update-info').textContent =
      json.updated ? `Diperbarui: ${json.updated}` : `Data: ${json.date}`;

    if (json.preferences && json.preferences.length > 0) {
      const section = document.getElementById('pref-section');
      const tags = document.getElementById('pref-tags');
      section.classList.remove('hidden');
      tags.innerHTML = json.preferences
        .map(p => `<span class="pref-tag">${CAT_ICONS[p] || '◈'} ${p}</span>`)
        .join('');
    }

    renderTrends(allTrends);
  } catch (e) {
    document.getElementById('trends-grid').innerHTML =
      `<div class="empty-state"><h3>Gagal memuat data</h3><p>Coba refresh halaman.</p></div>`;
  }
}

function renderTrends(trends) {
  const grid = document.getElementById('trends-grid');
  const filtered = activeFilter === 'semua'
    ? trends
    : trends.filter(t => t.kategori === activeFilter);

  if (filtered.length === 0) {
    grid.innerHTML = `<div class="empty-state"><h3>Tidak ada tren</h3><p>Coba filter lain.</p></div>`;
    return;
  }

  grid.innerHTML = filtered.map(t => cardHTML(t)).join('');
  grid.querySelectorAll('.save-btn').forEach(btn => {
    btn.addEventListener('click', () => toggleSave(btn.dataset.id));
  });
}

function cardHTML(t) {
  const catClass = 'cat-' + (t.kategori === 'visual identity' ? 'visual' : t.kategori);
  const tingkatClass = 'tingkat-' + t.tingkat;
  const isSaved = savedIds.has(t.id);
  const imgPart = t.image
    ? `<img class="card-image" src="${t.image}" alt="${t.title}" loading="lazy" onerror="this.outerHTML='<div class=\\'card-image-placeholder\\'>${CAT_ICONS[t.kategori] || '◈'}</div>'">`
    : `<div class="card-image-placeholder">${CAT_ICONS[t.kategori] || '◈'}</div>`;

  return `
<div class="card" data-id="${t.id}" data-kategori="${t.kategori}">
  ${imgPart}
  <div class="card-body">
    <div class="card-meta">
      <span class="cat-badge ${catClass}">${t.kategori}</span>
      <span class="tingkat-badge ${tingkatClass}">${t.tingkat}</span>
    </div>
    <h3 class="card-title">${t.title}</h3>
    <div class="teori-tag">${t.teori}</div>
    <p class="card-penjelasan">${t.penjelasan}</p>
    <div class="card-actions">
      <a href="${t.link}" target="_blank" rel="noopener" class="source-link">${t.source}</a>
      <button class="save-btn ${isSaved ? 'saved' : ''}" data-id="${t.id}">
        ${isSaved ? '♥ Tersimpan' : '♡ Simpan'}
      </button>
    </div>
  </div>
</div>`;
}

async function toggleSave(id) {
  const trend = allTrends.find(t => t.id === id);
  if (!trend) return;

  if (savedIds.has(id)) {
    await sb.from('saved_designs').delete().eq('id', id);
    savedIds.delete(id);
    showToast('Dihapus dari tersimpan');
  } else {
    await sb.from('saved_designs').insert([trend]);
    savedIds.add(id);
    showToast('♥ Tersimpan!');
  }

  updateSavedBadge();
  const btn = document.querySelector(`.save-btn[data-id="${id}"]`);
  if (btn) {
    btn.className = 'save-btn ' + (savedIds.has(id) ? 'saved' : '');
    btn.textContent = savedIds.has(id) ? '♥ Tersimpan' : '♡ Simpan';
  }
}

async function loadSavedPage() {
  const grid = document.getElementById('saved-grid');
  const { data } = await sb.from('saved_designs').select('*').order('saved_at', { ascending: false });

  if (!data || data.length === 0) {
    grid.innerHTML = `<div class="empty-state"><h3>Belum ada yang tersimpan</h3><p>Kembali ke <a href="index.html">Tren Hari Ini</a> dan klik ♡ Simpan.</p></div>`;
    return;
  }

  allTrends = data;
  grid.innerHTML = data.map(t => cardHTML(t)).join('');
  grid.querySelectorAll('.save-btn').forEach(btn => {
    btn.addEventListener('click', async () => {
      const id = btn.dataset.id;
      await sb.from('saved_designs').delete().eq('id', id);
      savedIds.delete(id);
      document.querySelector(`.card[data-id="${id}"]`).remove();
      showToast('Dihapus dari tersimpan');
      updateSavedBadge();
    });
  });
}

function setupFilters() {
  document.querySelectorAll('.filter-btn').forEach(btn => {
    btn.addEventListener('click', () => {
      document.querySelectorAll('.filter-btn').forEach(b => b.classList.remove('active'));
      btn.classList.add('active');
      activeFilter = btn.dataset.filter;
      renderTrends(allTrends);
    });
  });
}

function updateSavedBadge() {
  const badge = document.getElementById('saved-count');
  if (!badge) return;
  if (savedIds.size > 0) {
    badge.textContent = savedIds.size;
    badge.classList.remove('hidden');
  } else {
    badge.classList.add('hidden');
  }
}

function showToast(msg) {
  const toast = document.getElementById('toast');
  toast.textContent = msg;
  toast.classList.remove('hidden');
  setTimeout(() => toast.classList.add('hidden'), 2500);
}

init();

const sb = supabase.createClient(SUPABASE_URL, SUPABASE_KEY);

let allItems = [];
let savedIds = new Set();
let activeFilter = 'semua';

async function init() {
  await loadSavedIds();
  if (PAGE === 'index') {
    await loadArchive();
    setupFilters();
  } else {
    await loadSavedPage();
  }
  updateBadge();
}

async function loadSavedIds() {
  try {
    const { data } = await sb.from('saved_designs').select('id');
    savedIds = new Set((data || []).map(r => r.id));
  } catch (e) { savedIds = new Set(); }
}

async function loadArchive() {
  try {
    const res = await fetch('data/designs.json?t=' + Date.now());
    const json = await res.json();
    allItems = json.items || [];
    const info = document.getElementById('hero-label');
    if (info) info.textContent =
      `◖ ${allItems.length} KARYA DI ARSIP · UPDATE ${json.updated || '-'} ◗`;
    render();
  } catch (e) {
    document.getElementById('grid').innerHTML =
      `<div class="state"><h3>Gagal memuat data</h3><p>Coba refresh halaman.</p></div>`;
  }
}

function esc(s) {
  return String(s == null ? '' : s).replace(/[&<>"]/g, c =>
    ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;' }[c]));
}

function paletteHTML(pal) {
  if (!pal || !pal.length) return '';
  return `<div class="palette">${pal.slice(0, 4).map(c =>
    `<span style="background:${esc(c)}"></span>`).join('')}</div>`;
}

function cardHTML(it) {
  const img = it.image
    ? `<img class="card-img" src="${esc(it.image)}" alt="${esc(it.title)}" loading="lazy"
         onerror="this.outerHTML='<div class=\\'card-img-ph\\'>${esc((it.title||'?')[0])}</div>'">`
    : `<div class="card-img-ph">${esc((it.title || '?')[0])}</div>`;
  const bd = (it.breakdown || []).map(b => {
    const cls = 'bd-' + String(b.label || '').toUpperCase().replace(/[^A-Z]/g, '');
    return `<div class="bd-row"><span class="bd-label ${cls}">${esc(b.label)}</span><span class="bd-text">${esc(b.text)}</span></div>`;
  }).join('');
  const saved = savedIds.has(it.id);
  const isNew = it.date === (allItems[0] && allItems[0].date);
  return `
<div class="card" data-id="${esc(it.id)}" data-kat="${esc(it.kategori)}">
  ${isNew ? `<div class="sticker">NEW<br>★</div>` : ''}
  <div class="card-img-wrap">
    ${img}
    <span class="src-badge">◦ ${esc((it.source || '').toUpperCase())}</span>
    ${paletteHTML(it.palette)}
  </div>
  <div class="card-body">
    <div class="pills">
      <span class="pill pill-cat">${esc(it.kategori)}</span>
      <span class="pill pill-t ${esc(it.tingkat)}">${esc(it.tingkat)}</span>
    </div>
    <div class="card-title">${esc(it.title)}</div>
    ${it.teori && it.teori !== '-' ? `<div class="teori">${esc(it.teori)}</div>` : ''}
    <div class="breakdown">${bd}</div>
    ${it.pelajaran ? `<div class="pelajaran">${esc(it.pelajaran)}</div>` : ''}
    <div class="card-actions">
      <a class="src-link" href="${esc(it.link)}" target="_blank" rel="noopener">sumber</a>
      <button class="save-btn ${saved ? 'saved' : ''}" data-id="${esc(it.id)}">
        ${saved ? '♥ TERSIMPAN' : '♡ SIMPAN'}</button>
    </div>
  </div>
</div>`;
}

function render() {
  const grid = document.getElementById('grid');
  const list = activeFilter === 'semua'
    ? allItems : allItems.filter(i => i.kategori === activeFilter);
  if (!list.length) {
    grid.innerHTML = `<div class="state"><h3>Belum ada karya</h3><p>Tunggu update otomatis jam 09:00 WIB.</p></div>`;
    return;
  }
  grid.innerHTML = list.map(cardHTML).join('');
  bindSave(grid);
}

function bindSave(root) {
  root.querySelectorAll('.save-btn').forEach(btn =>
    btn.addEventListener('click', () => toggleSave(btn.dataset.id)));
}

async function toggleSave(id) {
  const it = allItems.find(i => i.id === id);
  if (!it) return;
  try {
    if (savedIds.has(id)) {
      await sb.from('saved_designs').delete().eq('id', id);
      savedIds.delete(id);
      toast('Dihapus dari tersimpan');
    } else {
      await sb.from('saved_designs').insert([{ id, data: it }]);
      savedIds.add(id);
      toast('♥ Tersimpan!');
    }
  } catch (e) { toast('Gagal — cek koneksi'); return; }
  updateBadge();
  const btn = document.querySelector(`.save-btn[data-id="${CSS.escape(id)}"]`);
  if (btn) {
    const s = savedIds.has(id);
    btn.className = 'save-btn' + (s ? ' saved' : '');
    btn.textContent = s ? '♥ TERSIMPAN' : '♡ SIMPAN';
  }
}

async function loadSavedPage() {
  const grid = document.getElementById('grid');
  let rows;
  try {
    const { data } = await sb.from('saved_designs')
      .select('data, saved_at').order('saved_at', { ascending: false });
    rows = data || [];
  } catch (e) { rows = []; }
  if (!rows.length) {
    grid.innerHTML = `<div class="state"><h3>Belum ada yang tersimpan</h3>
      <p>Buka <a href="index.html" style="color:var(--accent)">Tren Hari Ini</a> lalu klik ♡ Simpan.</p></div>`;
    return;
  }
  allItems = rows.map(r => r.data);
  grid.innerHTML = allItems.map(cardHTML).join('');
  grid.querySelectorAll('.save-btn').forEach(btn =>
    btn.addEventListener('click', async () => {
      const id = btn.dataset.id;
      await sb.from('saved_designs').delete().eq('id', id);
      savedIds.delete(id);
      document.querySelector(`.card[data-id="${CSS.escape(id)}"]`).remove();
      toast('Dihapus'); updateBadge();
    }));
}

function setupFilters() {
  document.querySelectorAll('.filter-btn').forEach(btn =>
    btn.addEventListener('click', () => {
      document.querySelectorAll('.filter-btn').forEach(b => b.classList.remove('active'));
      btn.classList.add('active');
      activeFilter = btn.dataset.filter;
      render();
    }));
}

function updateBadge() {
  const b = document.getElementById('saved-count');
  if (!b) return;
  if (savedIds.size) { b.textContent = savedIds.size; b.classList.remove('hidden'); }
  else b.classList.add('hidden');
}

function toast(msg) {
  const t = document.getElementById('toast');
  t.textContent = msg; t.classList.remove('hidden');
  setTimeout(() => t.classList.add('hidden'), 2200);
}

init();

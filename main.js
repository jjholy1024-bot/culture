// ─── 데이터 경로 ──────────────────────────────────
const COUNTRIES_URL = './public/data/countries.json';
const COUNTRY_DETAIL_URL = iso => `./public/data/countries/${iso}.json`;

// 한국인 여행자 기준 인기 국가 (ISO3)
const POPULAR_ISO = ['JPN', 'USA', 'FRA', 'GBR', 'THA', 'VNM', 'CHN', 'AUS', 'DEU', 'ITA'];

const ALERT_COLORS = {
  '없음': '#3B7D2E',
  '여행유의': '#2E5B9D',
  '여행자제': '#C77700',
  '철수권고': '#D45500',
  '여행금지': '#C0392B',
};

// ─── 상태 ────────────────────────────────────────
let ALL_COUNTRIES = [];
let currentView = 'map';
let mapInstance = null;
let currentDetail = null;

// ─── 유틸 ────────────────────────────────────────
function showToast(msg) {
  const t = document.getElementById('toast');
  t.textContent = msg;
  t.classList.add('show');
  setTimeout(() => t.classList.remove('show'), 2200);
}

function findCountry(query) {
  const q = query.trim().toLowerCase();
  if (!q) return [];
  return ALL_COUNTRIES.filter(c =>
    c.country_kr.toLowerCase().includes(q) ||
    c.country_en.toLowerCase().includes(q) ||
    c.iso_code.toLowerCase() === q
  ).slice(0, 8);
}

// ─── 화면 전환 ───────────────────────────────────
function showScreen(name) {
  document.getElementById('screenHome').style.display = name === 'home' ? '' : 'none';
  document.getElementById('screenLoading').style.display = name === 'loading' ? '' : 'none';
  document.getElementById('screenResult').style.display = name === 'result' ? '' : 'none';
}

function goHome() {
  showScreen('home');
  document.getElementById('searchInput').value = '';
  document.getElementById('searchSuggest').style.display = 'none';
  history.replaceState(null, '', location.pathname);
}

// ─── 검색 ────────────────────────────────────────
function renderSuggestions(query) {
  const box = document.getElementById('searchSuggest');
  const matches = findCountry(query);
  if (!query.trim()) { box.style.display = 'none'; return; }
  if (matches.length === 0) {
    box.innerHTML = '<div class="suggest-empty">검색 결과가 없어요</div>';
  } else {
    box.innerHTML = matches.map(c => `
      <div class="suggest-item" onclick="selectCountry('${c.iso_code}')">
        <img class="suggest-flag" src="${c.flag_image || ''}" alt="" onerror="this.style.visibility='hidden'" />
        <span>${c.country_kr} <span style="color:#aaa;">(${c.country_en})</span></span>
      </div>`).join('');
  }
  box.style.display = 'block';
}

document.getElementById('searchInput').addEventListener('input', e => {
  const v = e.target.value;
  document.getElementById('searchClear').style.display = v ? 'block' : 'none';
  renderSuggestions(v);
});

document.getElementById('searchInput').addEventListener('keydown', e => {
  if (e.key === 'Enter') {
    const matches = findCountry(e.target.value);
    if (matches.length > 0) selectCountry(matches[0].iso_code);
  }
});

document.getElementById('searchClear').addEventListener('click', () => {
  document.getElementById('searchInput').value = '';
  document.getElementById('searchClear').style.display = 'none';
  document.getElementById('searchSuggest').style.display = 'none';
});

document.addEventListener('click', e => {
  const wrap = document.querySelector('.search-wrap-hero');
  if (wrap && !wrap.contains(e.target)) {
    document.getElementById('searchSuggest').style.display = 'none';
  }
});

// ─── 인기 국가 칩 ────────────────────────────────
function renderChips() {
  const box = document.getElementById('popularChips');
  const chips = POPULAR_ISO
    .map(iso => ALL_COUNTRIES.find(c => c.iso_code === iso))
    .filter(Boolean);
  box.innerHTML = chips.map(c => `
    <div class="chip" onclick="selectCountry('${c.iso_code}')">
      <img src="${c.flag_image || ''}" alt="" onerror="this.style.visibility='hidden'" />
      <span>${c.country_kr}</span>
    </div>`).join('');
}

// ─── 지도 / 리스트 뷰 ────────────────────────────
function renderMap() {
  if (!mapInstance) {
    mapInstance = L.map('map', { minZoom: 2, maxBoundsViscosity: 1.0, worldCopyJump: false })
      .setView([20, 10], 2);
    mapInstance.setMaxBounds([[-85, -180], [85, 180]]);
    L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
      attribution: '© OpenStreetMap contributors',
      noWrap: true,
    }).addTo(mapInstance);
  } else {
    mapInstance.eachLayer(l => { if (l instanceof L.Marker) mapInstance.removeLayer(l); });
  }

  ALL_COUNTRIES.forEach(c => {
    if (!c.lat && !c.lng) return;
    const color = ALERT_COLORS[c.alert_level] || ALERT_COLORS['없음'];
    const icon = L.divIcon({
      html: `<div style="background:${color};width:14px;height:14px;border-radius:50%;
        border:2px solid #fff;box-shadow:0 1px 4px rgba(0,0,0,0.4);"></div>`,
      className: '', iconSize: [14, 14], iconAnchor: [7, 7],
    });
    L.marker([c.lat, c.lng], { icon })
      .addTo(mapInstance)
      .bindTooltip(`${c.country_kr} · ${c.alert_level}`)
      .on('click', () => selectCountry(c.iso_code));
  });

  setTimeout(() => mapInstance.invalidateSize(), 100);
}

function renderLegend() {
  const box = document.getElementById('mapLegend');
  box.innerHTML = Object.entries(ALERT_COLORS).map(([level, color]) => `
    <div class="legend-item">
      <span class="legend-dot" style="background:${color};"></span>${level}
    </div>`).join('');
}

function renderList() {
  const box = document.getElementById('listView');
  box.innerHTML = ALL_COUNTRIES.map(c => `
    <div class="country-card" onclick="selectCountry('${c.iso_code}')">
      <img src="${c.flag_image || ''}" alt="" onerror="this.style.visibility='hidden'" />
      <div>
        <p class="country-card-name">${c.country_kr}</p>
        <span class="alert-badge alert-${c.alert_level}">${c.alert_level}</span>
      </div>
    </div>`).join('');
}

document.querySelectorAll('.view-btn').forEach(btn => {
  btn.addEventListener('click', () => {
    document.querySelectorAll('.view-btn').forEach(b => b.classList.remove('active'));
    btn.classList.add('active');
    currentView = btn.dataset.view;
    document.getElementById('mapView').style.display = currentView === 'map' ? '' : 'none';
    document.getElementById('listView').style.display = currentView === 'list' ? 'grid' : 'none';
    if (currentView === 'map') setTimeout(() => mapInstance && mapInstance.invalidateSize(), 50);
  });
});

// ─── 국가 선택 → 브리핑 로딩 ─────────────────────
async function selectCountry(iso) {
  showScreen('loading');
  document.querySelectorAll('.loading-steps li').forEach(li => li.classList.remove('done'));
  history.replaceState(null, '', `?country=${iso}`);

  try {
    const res = await fetch(COUNTRY_DETAIL_URL(iso));
    if (!res.ok) throw new Error('not found');
    const detail = await res.json();
    currentDetail = detail;

    // 단계별 진행 표시(연출용)
    const steps = ['alert', 'accident', 'contact', 'culture'];
    for (const step of steps) {
      await new Promise(r => setTimeout(r, 120));
      const li = document.querySelector(`.loading-steps li[data-step="${step}"]`);
      if (li) li.classList.add('done');
    }
    await new Promise(r => setTimeout(r, 150));

    renderResult(detail);
    showScreen('result');
  } catch (err) {
    console.error('브리핑 로딩 실패:', err);
    showToast('해당 국가 정보를 불러오지 못했어요');
    showScreen('home');
  }
}

// ─── 결과 화면 렌더링 ────────────────────────────
function renderResult(d) {
  document.getElementById('resultFlag').src = d.flag_image || '';
  document.getElementById('resultCountryName').textContent = d.country_kr;

  const level = d.travel_alert?.level || '없음';
  const badge = document.getElementById('resultAlertBadge');
  badge.textContent = `여행경보: ${level}`;
  badge.className = `alert-badge alert-${level}`;

  document.getElementById('noticeLink').href = d.notice_url || 'https://www.0404.go.kr/ntnSafetyInfo/list';

  const regions = d.travel_alert?.regions || [];
  const regionsHTML = regions.length
    ? `<div class="alert-region-list">${regions.map(r => `
        <div class="alert-region-item">
          <span class="alert-badge alert-${r.level}">${r.level}</span>
          <span class="alert-region-area">${r.area || '전 지역'}${r.partial ? ' (일부)' : ''}</span>
        </div>`).join('')}</div>`
    : `<p class="brief-empty">현재 발령된 여행경보가 없어요.</p>`;

  const ai = d.culture_ai;
  const phrasesHTML = ai?.phrases?.length
    ? `<ul class="phrase-list">${ai.phrases.map(p => `<li>${p}</li>`).join('')}</ul>`
    : `<p class="brief-empty">준비 중이에요.</p>`;

  const cards = [
    {
      icon: '🛡️', title: '사건사고 예방정보', source: 'official',
      body: d.accident_info_html || '<p class="brief-empty">등록된 정보가 없어요.</p>',
    },
    {
      icon: '🚦', title: '여행경보 단계 상세', source: 'official',
      body: regionsHTML,
    },
    {
      icon: '📞', title: '긴급 연락처', source: 'official',
      body: d.local_contact_html || '<p class="brief-empty">등록된 정보가 없어요.</p>',
    },
    {
      icon: '🤝', title: '문화·예절', source: 'ai',
      body: ai?.etiquette ? `<p>${ai.etiquette}</p>` : '<p class="brief-empty">준비 중이에요.</p>',
    },
    {
      icon: '💼', title: '비즈니스 팁', source: 'ai',
      body: ai?.business_tip ? `<p>${ai.business_tip}</p>` : '<p class="brief-empty">준비 중이에요.</p>',
    },
    {
      icon: '💬', title: '유용한 현지 표현', source: 'ai',
      body: phrasesHTML,
    },
  ];

  document.getElementById('resultCards').innerHTML = cards.map(c => `
    <div class="brief-card">
      <div class="brief-card-head">
        <span class="brief-card-title">${c.icon} ${c.title}</span>
        <span class="source-badge source-${c.source}">${c.source === 'official' ? '외교부 데이터' : 'AI 생성'}</span>
      </div>
      <div class="brief-card-body">${c.body}</div>
    </div>`).join('');
}

// ─── 공유 ────────────────────────────────────────
function shareResult() {
  if (!currentDetail) return;
  const url = `${location.href.split('?')[0]}?country=${currentDetail.iso_code}`;
  navigator.clipboard.writeText(url).catch(() => {});
  showToast('🔗 링크가 복사되었어요');
}

// ─── 데이터 로딩 ─────────────────────────────────
async function loadData() {
  try {
    const res = await fetch(COUNTRIES_URL);
    ALL_COUNTRIES = await res.json();
  } catch (err) {
    console.error('국가 목록 로딩 실패:', err);
    showToast('데이터를 불러오지 못했어요');
    return;
  }

  renderChips();
  renderLegend();
  renderMap();
  renderList();

  const params = new URLSearchParams(location.search);
  const iso = params.get('country');
  if (iso && ALL_COUNTRIES.some(c => c.iso_code === iso)) {
    selectCountry(iso);
  }
}

loadData();

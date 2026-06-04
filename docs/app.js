/* PHONE_INTEL — client-side live demo (GitHub Pages).
   Parses entirely in the browser with libphonenumber-js. No backend, no network
   calls, no data stored. Honest subset: country / validity / type / formats +
   offline map + risk heuristic. Carrier, city-level region, and per-number
   timezone are NOT shown here (they need the full Python app — not faked). */
'use strict';

// ---------- Matrix rain ----------
(function matrixRain() {
    const c = document.getElementById('matrix');
    const ctx = c.getContext('2d');
    let cols, drops;
    const chars = '01ｱｲｳｴｵｶｷｸ#%@&$<>/|=+*ﾊﾋﾎﾏﾐﾑﾒ'.split('');
    function resize() {
        c.width = window.innerWidth; c.height = window.innerHeight;
        cols = Math.floor(c.width / 14);
        drops = Array(cols).fill(0).map(() => Math.random() * -50);
    }
    resize();
    window.addEventListener('resize', resize);
    function draw() {
        ctx.fillStyle = 'rgba(3,5,10,0.08)';
        ctx.fillRect(0, 0, c.width, c.height);
        ctx.font = '14px monospace';
        for (let i = 0; i < cols; i++) {
            const ch = chars[Math.floor(Math.random() * chars.length)];
            const x = i * 14, y = drops[i] * 14;
            ctx.fillStyle = Math.random() > 0.975 ? '#ccffcc' : '#00aa2e';
            ctx.fillText(ch, x, y);
            if (y > c.height && Math.random() > 0.975) drops[i] = 0;
            drops[i] += 0.5;
        }
    }
    setInterval(draw, 55);
})();

// ---------- Quick hints ----------
const HINTS = [
    ['🇺🇸 US', '+14155552671'], ['🇬🇧 UK', '+442079460958'],
    ['🇵🇭 PH', '+639171234567'], ['🇯🇵 JP', '+819012345678'],
    ['🇩🇪 DE', '+4915112345678'], ['🇧🇷 BR', '+5511912345678'],
    ['🇦🇺 AU', '+61412345678'], ['🇮🇳 IN', '+919812345678'],
];
const hintsEl = document.getElementById('hints');
HINTS.forEach(([label, num]) => {
    const s = document.createElement('span');
    s.className = 'hint'; s.textContent = label;
    s.onclick = () => { input.value = num; doScan(); };
    hintsEl.appendChild(s);
});

// ---------- Elements ----------
const input = document.getElementById('phoneInput');
const btn = document.getElementById('searchBtn');
const err = document.getElementById('errMsg');
const card = document.getElementById('resultCard');
const overlay = document.getElementById('scanOverlay');
const bar = document.getElementById('scanBar');
const status = document.getElementById('scanStatus');
const grid = document.getElementById('infoGrid');
let map = null, lastData = null;
let worldGeo = null, mapBaseAdded = false;

fetch('vendor/world.geo.json').then(r => r.json())
    .then(g => { worldGeo = g; addBasemap(); })
    .catch(() => { /* map still works without land polygons */ });

function addBasemap() {
    if (!map || mapBaseAdded || !worldGeo) return;
    L.geoJSON(worldGeo, {
        interactive: false, pane: 'basemap',
        style: { color: '#12482b', weight: 1, fillColor: '#0a1f12', fillOpacity: 1 }
    }).addTo(map);
    mapBaseAdded = true;
}

btn.onclick = doScan;
input.addEventListener('keydown', e => { if (e.key === 'Enter') doScan(); });
const sleep = ms => new Promise(r => setTimeout(r, ms));

const PHASES = [
    [16, 'parsing E.164 structure...'],
    [38, 'querying libphonenumber dataset...'],
    [60, 'resolving country numbering plan...'],
    [78, 'detecting line type...'],
    [92, 'plotting registration region...'],
    [100, 'compiling intel report...'],
];

const TYPE_LABELS = {
    MOBILE: 'Mobile', FIXED_LINE: 'Fixed line',
    FIXED_LINE_OR_MOBILE: 'Fixed line or mobile', TOLL_FREE: 'Toll-free',
    PREMIUM_RATE: 'Premium rate', SHARED_COST: 'Shared cost', VOIP: 'VoIP',
    PERSONAL_NUMBER: 'Personal number', PAGER: 'Pager', UAN: 'Universal access number',
    VOICEMAIL: 'Voicemail',
};

function flag(iso) {
    if (!iso || iso.length !== 2) return '🌐';
    return String.fromCodePoint(...[...iso.toUpperCase()].map(c => 0x1F1E6 + c.charCodeAt(0) - 65));
}

// Client-side port of the offline risk heuristic (carrier signal omitted —
// carrier isn't available in the browser, so we never guess it).
function assess(d) {
    if (!d.parsed) return { level: 'UNKNOWN', score: 0, reasons: ['Number could not be parsed.'] };
    let score = 0; const reasons = [];
    if (!d.valid) { score += 40; reasons.push('Fails validation for its country numbering plan.'); }
    switch (d.typeCode) {
        case 'PREMIUM_RATE': score += 70; reasons.push('Premium-rate line — frequently abused for billing scams.'); break;
        case 'SHARED_COST': score += 30; reasons.push('Shared-cost line — treat unsolicited contact with caution.'); break;
        case 'VOIP': score += 25; reasons.push('VoIP line — cheap/disposable, common for spam & spoofing.'); break;
        case 'PERSONAL_NUMBER': score += 15; reasons.push('Personal-number service — can mask the real line.'); break;
        case 'TOLL_FREE': reasons.push('Toll-free line — typically a business/support number.'); break;
    }
    if (!reasons.length) reasons.push('No structural risk signals detected.');
    score = Math.max(0, Math.min(100, score));
    const level = score >= 60 ? 'HIGH' : score >= 25 ? 'MEDIUM' : 'LOW';
    return { level, score, reasons };
}

function analyze(raw) {
    const d = { input: raw, parsed: false, valid: false };
    let n;
    try { n = libphonenumber.parsePhoneNumber(raw); }
    catch (e) { d.error = e.message === 'NOT_A_NUMBER' ? "That doesn't look like a phone number." : 'Could not parse number — include the country code (+...).'; return d; }
    if (!n) { d.error = 'Could not parse number — include the country code (+...).'; return d; }
    d.parsed = true;
    d.valid = n.isValid();
    d.iso = n.country || null;
    d.calling_code = n.countryCallingCode ? ('+' + n.countryCallingCode) : null;
    d.e164 = n.number;
    d.national = n.formatNational();
    d.international = n.formatInternational();
    d.uri = n.getURI();
    d.typeCode = n.getType() || null;
    d.line_type = d.typeCode ? (TYPE_LABELS[d.typeCode] || d.typeCode) : 'Unknown';
    d.national_number = String(n.nationalNumber);
    const c = d.iso && COUNTRIES[d.iso];
    d.country_name = c ? c.name : (d.iso || null);
    d.country_flag = flag(d.iso);
    d.lat = c ? c.lat : null;
    d.lng = c ? c.lng : null;
    if (!d.valid) d.error = 'Number is not valid for its country (parsed, but fails validation).';
    return d;
}

async function doScan() {
    const raw = input.value.trim();
    err.classList.remove('show');
    if (!raw) { showErr('⚠ Enter a phone number (include country code).'); return; }
    overlay.classList.add('active'); btn.disabled = true; bar.style.width = '0%';
    for (const [pct, msg] of PHASES) {
        await sleep(130 + Math.random() * 150);
        bar.style.width = pct + '%'; status.textContent = msg;
    }
    const d = analyze(raw);
    await sleep(180);
    overlay.classList.remove('active'); btn.disabled = false;
    if (!d.parsed) { showErr('❌ ' + (d.error || 'Cannot parse number.')); card.classList.remove('active'); return; }
    render(d);
}

function showErr(m) { err.textContent = m; err.classList.add('show'); }

function esc(s) {
    return String(s == null ? '' : s).replace(/[&<>"']/g,
        c => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[c]));
}
function tile(lbl, val, cls = '') {
    const v = (val === null || val === undefined || val === '') ? '—' : val;
    return `<div class="tile"><div class="lbl">${lbl}</div><div class="val ${cls}">${v}</div></div>`;
}

function render(d) {
    lastData = d;
    document.getElementById('resNum').textContent = (d.country_flag || '🌐') + ' ' + (d.international || d.input);
    const badge = document.getElementById('resBadge');
    if (d.valid) { badge.textContent = 'VALID'; badge.className = 'badge ok'; }
    else { badge.textContent = 'INVALID'; badge.className = 'badge warn'; }

    grid.innerHTML = [
        tile('COUNTRY', `<span class="flag">${d.country_flag || '🌐'}</span>${esc(d.country_name || d.iso || '?')}`),
        tile('CALLING CODE', d.calling_code, 'green'),
        tile('ISO', d.iso),
        tile('LINE TYPE', esc(d.line_type)),
        tile('E.164', esc(d.e164), 'green'),
        tile('NATIONAL', esc(d.national)),
        tile('INTERNATIONAL', esc(d.international)),
        tile('NATIONAL NUMBER', esc(d.national_number)),
        tile('CARRIER · REGION · TZ', 'full app only — not faked here', 'dim'),
    ].join('');

    renderRisk(assess(d));
    renderMap(d);
    renderActions(d);
    card.classList.add('active');
    card.scrollIntoView({ behavior: 'smooth', block: 'start' });
}

function renderRisk(rep) {
    const b = document.getElementById('riskBar');
    if (!rep) { b.innerHTML = ''; return; }
    const reasons = (rep.reasons || []).map(r => `<li>${esc(r)}</li>`).join('');
    b.innerHTML =
        `<div class="risk-chip risk-${rep.level}">⚠ RISK: ${rep.level} · ${rep.score}/100
         <span style="opacity:.6">(heuristic, not a spam-DB verdict)</span></div>
         <ul class="risk-reasons">${reasons}</ul>`;
}

function renderMap(d) {
    const wrap = document.getElementById('mapWrap');
    if (d.lat == null || d.lng == null) { wrap.style.display = 'none'; return; }
    wrap.style.display = 'block';
    if (!map) {
        map = L.map('map', { zoomControl: true, attributionControl: true, minZoom: 1, maxZoom: 8, worldCopyJump: true }).setView([d.lat, d.lng], 4);
        map.createPane('basemap');
        map.getPane('basemap').style.zIndex = 350;
        map.attributionControl.addAttribution('Boundaries: Natural Earth (public domain)');
        addBasemap();
    } else {
        map.setView([d.lat, d.lng], 4);
    }
    if (map._pin) map.removeLayer(map._pin);
    map._pin = L.circleMarker([d.lat, d.lng], {
        radius: 11, color: '#00ff41', fillColor: '#00ff41', fillOpacity: 0.25, weight: 2
    }).addTo(map).bindPopup(
        `<b>${esc(d.country_name || d.iso)}</b><br>Country centroid<br>` +
        `<i style="color:#888">registration country — not a person's location</i>`
    );
    setTimeout(() => map.invalidateSize(), 120);
}

function renderActions(d) {
    document.getElementById('copyBtn').onclick = () => {
        navigator.clipboard.writeText(JSON.stringify(d, null, 2));
        flash(document.getElementById('copyBtn'), '✓ COPIED');
    };
    document.getElementById('dlBtn').onclick = () => {
        const blob = new Blob([JSON.stringify(d, null, 2)], { type: 'application/json' });
        const a = document.createElement('a');
        a.href = URL.createObjectURL(blob);
        a.download = 'intel_' + (d.e164 || 'number').replace(/[^\d]/g, '') + '.json';
        a.click();
    };
    document.getElementById('telLink').href = d.uri || ('tel:' + (d.e164 || ''));
}
function flash(el, txt) { const o = el.textContent; el.textContent = txt; setTimeout(() => { el.textContent = o; }, 1200); }

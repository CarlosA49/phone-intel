/* PHONE_INTEL web terminal — thin client over the Flask/Python engine.
   Real data only. The matrix rain and scan drama are pure cosmetics. */
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
let map = null, clockTimers = [], lastData = null;
let worldGeo = null, mapBaseAdded = false;

// Preload the vendored world polygons so the map is fully offline (no tiles).
fetch('/static/vendor/world.geo.json')
    .then(r => r.json())
    .then(g => { worldGeo = g; addBasemap(); })
    .catch(() => { /* map still works, just without land polygons */ });

function addBasemap() {
    if (!map || mapBaseAdded || !worldGeo) return;
    // Render into a dedicated pane BELOW the overlay pane that holds the pin, so
    // a late-arriving basemap can never paint over the marker (z-order race).
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
    [12, 'acquiring target signature...'],
    [28, 'querying libphonenumber dataset...'],
    [46, 'resolving country numbering plan...'],
    [64, 'mapping carrier prefix...'],
    [80, 'triangulating registration region...'],
    [92, 'syncing timezone clock...'],
    [100, 'compiling intel report...'],
];

async function doScan() {
    const number = input.value.trim();
    err.classList.remove('show');
    if (!number) { showErr('⚠ Enter a phone number (include country code).'); return; }

    overlay.classList.add('active');
    btn.disabled = true;
    bar.style.width = '0%';

    const live = document.getElementById('liveChk').checked ? '1' : '0';
    const spam = document.getElementById('spamChk').checked ? '1' : '0';
    const fetchP = fetch(`/api/lookup?number=${encodeURIComponent(number)}&live=${live}&spam=${spam}`)
        .then(r => r.json()).catch(e => ({ ok: false, error: 'network error: ' + e }));

    for (const [pct, msg] of PHASES) {
        await sleep(140 + Math.random() * 160);
        bar.style.width = pct + '%';
        status.textContent = msg;
    }

    const data = await fetchP;
    await sleep(200);
    overlay.classList.remove('active');
    btn.disabled = false;

    if (!data || (!data.ok && !data.valid && data.error && !data.e164)) {
        showErr('❌ ' + (data.error || 'Cannot parse number. Include country code (+...).'));
        card.classList.remove('active');
        return;
    }
    render(data);
}

function showErr(m) { err.textContent = m; err.classList.add('show'); }

// Escape values that originate OUTSIDE libphonenumber (e.g. the NumVerify live
// API) before they ever touch innerHTML. libphonenumber-derived fields are a
// trusted dataset, but external/MITM-reachable data must be neutralised.
function escapeHtml(s) {
    return String(s == null ? '' : s).replace(/[&<>"']/g,
        c => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[c]));
}

function tile(lbl, val, cls = '') {
    const v = (val === null || val === undefined || val === '') ? '—' : val;
    return `<div class="tile"><div class="lbl">${lbl}</div><div class="val ${cls}">${v}</div></div>`;
}

function render(d) {
    lastData = d;
    clockTimers.forEach(clearInterval);
    clockTimers = [];

    document.getElementById('resNum').textContent =
        (d.country_flag || '🌐') + ' ' + (d.international || d.input);
    const badge = document.getElementById('resBadge');
    if (d.valid) { badge.textContent = 'VALID'; badge.className = 'badge ok'; }
    else if (d.ok) { badge.textContent = 'INVALID'; badge.className = 'badge warn'; }
    else { badge.textContent = 'UNPARSED'; badge.className = 'badge bad'; }

    // Live (NumVerify) values are external data — escape before innerHTML.
    const liveExtra = d.live
        ? (d.live.error
            ? tile('LIVE · ERROR', '⚠ ' + escapeHtml(d.live.error), 'bad')
            : tile('LIVE · CARRIER',
                escapeHtml(d.live.carrier || '—') + ' / ' + escapeHtml(d.live.line_type || '—'), 'mono'))
        : '';

    // Live fraud/spam DB (IPQualityScore) — also external, also escaped.
    const spamExtra = d.spam
        ? (d.spam.error
            ? tile('FRAUD DB · ERROR', '⚠ ' + escapeHtml(d.spam.error), 'bad')
            : tile('FRAUD DB (live)',
                escapeHtml(d.spam.level) + ' · score ' + escapeHtml(d.spam.fraud_score) +
                ' · abuse=' + escapeHtml(d.spam.recent_abuse) + ' risky=' + escapeHtml(d.spam.risky),
                d.spam.level === 'HIGH' ? 'bad' : (d.spam.level === 'LOW' ? 'green' : 'mono')))
        : '';

    // One live clock per IANA timezone the number maps to (CLI parity).
    const clockTiles = (d.local_times || []).map((t, i) =>
        tile(i === 0 ? 'LOCAL TIME ⏱' : 'LOCAL TIME',
            `<span class="clock" id="liveclock_${i}">${t.clock}</span> ${t.utc_offset} ` +
            `<span class="clock-tz">${t.tz}</span>`)
    ).join('');

    grid.innerHTML = [
        tile('COUNTRY', `<span class="flag">${d.country_flag || '🌐'}</span>${d.country_name || d.country_iso || '?'}`),
        tile('CALLING CODE', d.calling_code ? '+' + d.calling_code : '—', 'green'),
        tile('ISO / CAPITAL', `${d.country_iso || '—'} · ${d.capital || '—'}`),
        tile('REGION (registration)', d.region, 'mono'),
        tile('CARRIER', d.carrier, 'mono'),
        tile('LINE TYPE', d.line_type),
        tile('E.164', d.e164, 'green'),
        tile('NATIONAL', d.national),
        tile('AREA / SUBSCRIBER', `${d.area_code || '—'} / ${d.subscriber_number || '—'}`),
        clockTiles,
        (d.local_times && d.local_times.length) ? '' : tile('TIMEZONE', (d.timezones || []).join(', ') || '—'),
        liveExtra,
        spamExtra,
    ].join('');

    // Tick every zone's clock once per second.
    (d.local_times || []).forEach((t, i) => {
        const fmt = new Intl.DateTimeFormat('en-GB', {
            timeZone: t.tz, hour: '2-digit', minute: '2-digit', second: '2-digit', hour12: false });
        clockTimers.push(setInterval(() => {
            const el = document.getElementById('liveclock_' + i);
            if (el) el.textContent = fmt.format(new Date());
        }, 1000));
    });

    renderRisk(d.reputation);
    renderMap(d);
    renderActions(d);

    card.classList.add('active');
    card.scrollIntoView({ behavior: 'smooth', block: 'start' });
}

function renderRisk(rep) {
    const bar = document.getElementById('riskBar');
    if (!rep) { bar.innerHTML = ''; return; }
    const reasons = (rep.reasons || []).map(r => `<li>${r}</li>`).join('');
    bar.innerHTML =
        `<div class="risk-chip risk-${rep.level}">⚠ RISK: ${rep.level} · ${rep.score}/100
         <span style="opacity:.6">(heuristic, not a spam-DB verdict)</span></div>
         <ul class="risk-reasons">${reasons}</ul>`;
}

function renderMap(d) {
    const wrap = document.getElementById('mapWrap');
    if (d.lat == null || d.lng == null) { wrap.style.display = 'none'; return; }
    wrap.style.display = 'block';
    if (!map) {
        map = L.map('map', {
            zoomControl: true, attributionControl: true,
            minZoom: 1, maxZoom: 8, worldCopyJump: true
        }).setView([d.lat, d.lng], 4);
        // Pane below overlayPane (400) but above tilePane (200) for the basemap.
        map.createPane('basemap');
        map.getPane('basemap').style.zIndex = 350;
        map.attributionControl.addAttribution('Boundaries: Natural Earth (public domain)');
        addBasemap();   // vendored offline polygons (loads async; no-op until ready)
    } else {
        map.setView([d.lat, d.lng], 4);
    }
    if (map._pin) map.removeLayer(map._pin);
    map._pin = L.circleMarker([d.lat, d.lng], {
        radius: 11, color: '#00ff41', fillColor: '#00ff41', fillOpacity: 0.25, weight: 2
    }).addTo(map).bindPopup(
        `<b>${d.country_name || d.country_iso}</b><br>` +
        `Registration region:<br>${d.region || '—'}<br>` +
        `<i style="color:#888">country centroid — not a person's location</i>`
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
    const tel = document.getElementById('telLink');
    tel.href = d.rfc3966 || ('tel:' + (d.e164 || ''));
}

function flash(el, txt) {
    const old = el.textContent; el.textContent = txt;
    setTimeout(() => { el.textContent = old; }, 1200);
}

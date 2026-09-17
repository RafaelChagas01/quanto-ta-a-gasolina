const BOARD_ORDER = ['gasolina', 'gasolina_aditivada', 'etanol', 'diesel_s10', 'diesel', 'gnv', 'glp'];
const CHART_PRODUCTS = ['gasolina', 'etanol', 'diesel_s10', 'diesel', 'gnv', 'glp'];
const ETANOL_LIMIT = 0.7;
const RANKING_SIZE = 10;
const DEFAULT_UF = 'SP';
const DEFAULT_CITY = 'sao-paulo';

const el = (id) => document.getElementById(id);
const cache = new Map();
let meta = null;
let current = { uf: null, city: null, product: 'gasolina' };

const money = (value) => value.toFixed(2).replace('.', ',');
const shortDate = (iso) => `${iso.slice(8, 10)}/${iso.slice(5, 7)}`;

function weekRange(iso) {
  const end = new Date(`${iso}T12:00:00Z`);
  const start = new Date(end.getTime() - 6 * 86400000);
  return `${shortDate(start.toISOString())} a ${shortDate(iso)}`;
}

// passo "redondo" pro eixo: 0,05 / 0,10 / 0,25 / 0,50 / 1 ...
function niceScale(lo, hi, maxTicks = 4) {
  const steps = [0.05, 0.1, 0.2, 0.25, 0.5, 1, 2, 5, 10, 20, 50];
  const step = steps.find((s) => (hi - lo) / s <= maxTicks) || 100;
  const min = Math.floor(lo / step) * step;
  const max = Math.ceil(hi / step) * step;
  const ticks = [];
  for (let v = min; v <= max + step / 2; v += step) ticks.push(Math.round(v * 100) / 100);
  return { min, max: max === min ? max + step : max, ticks };
}

function node(tag, props = {}, children = []) {
  const item = document.createElement(tag);
  for (const [name, value] of Object.entries(props)) {
    if (name === 'text') item.textContent = value;
    else if (name === 'className') item.className = value;
    else item.setAttribute(name, value);
  }
  for (const child of children) item.append(child);
  return item;
}

function svg(tag, attrs = {}, text) {
  const item = document.createElementNS('http://www.w3.org/2000/svg', tag);
  for (const [name, value] of Object.entries(attrs)) item.setAttribute(name, value);
  if (text !== undefined) item.textContent = text;
  return item;
}

async function getJson(path) {
  const res = await fetch(path, { credentials: 'omit' });
  if (!res.ok) throw new Error(`HTTP ${res.status}`);
  return res.json();
}

async function loadState(uf) {
  // so aceita UF que veio no meta.json
  if (!meta.states.some((s) => s.uf === uf)) throw new Error('estado invalido');
  if (!cache.has(uf)) cache.set(uf, await getJson(`data/uf/${uf}.json`));
  return cache.get(uf);
}

function lastPoint(points, maxWeek) {
  if (!points) return null;
  for (let i = points.length - 1; i >= 0; i--) {
    if (points[i][0] <= maxWeek) return points[i];
  }
  return null;
}

function readUrl() {
  const params = new URLSearchParams(location.search);
  return {
    uf: (params.get('uf') || '').toUpperCase(),
    city: params.get('cidade') || '',
    product: params.get('combustivel') || '',
  };
}

function writeUrl() {
  const params = new URLSearchParams({ uf: current.uf, cidade: current.city, combustivel: current.product });
  history.replaceState(null, '', `?${params}`);
}

function fillStates() {
  const select = el('state');
  select.replaceChildren(...meta.states.map((s) => node('option', { value: s.uf, text: s.name })));
  select.value = current.uf;
  select.disabled = false;
}

function fillCities(state) {
  const select = el('city');
  select.replaceChildren(...state.cities.map((c) => node('option', { value: c.slug, text: c.name })));
  select.value = current.city;
  select.disabled = false;
}

function fillProducts() {
  const select = el('product');
  select.replaceChildren(...CHART_PRODUCTS.map((p) => node('option', { value: p, text: meta.products[p].label })));
  select.value = current.product;
}

function renderBoard(city) {
  const latest = meta.weeks.length - 1;
  const cityLatest = Math.max(...Object.values(city.prices).map((pts) => pts[pts.length - 1][0]));

  el('board-city').textContent = city.name;
  el('board-week').textContent = cityLatest === latest
    ? `Pesquisa de ${weekRange(meta.weeks[latest])}`
    : `Última pesquisa na cidade: ${weekRange(meta.weeks[cityLatest])}`;

  const items = BOARD_ORDER.map((product) => {
    const info = meta.products[product];
    const points = city.prices[product];
    const point = lastPoint(points, cityLatest);
    const name = node('span', { className: 'fuel-name', text: info.label }, [node('span', { className: 'fuel-unit', text: info.unit })]);

    if (!point || point[0] !== cityLatest) {
      return node('li', {}, [name, node('span', { className: 'fuel-missing', text: 'sem pesquisa' })]);
    }

    const price = node('span', { className: 'fuel-price' }, [node('small', { text: 'R$' }), money(point[1])]);
    const previous = points.find((p) => p[0] === point[0] - 1);
    let change = null;
    if (previous) {
      const diff = Math.round((point[1] - previous[1]) * 100) / 100;
      if (diff > 0) change = node('span', { className: 'fuel-change up', text: `subiu R$ ${money(diff)} na semana` });
      else if (diff < 0) change = node('span', { className: 'fuel-change down', text: `caiu R$ ${money(-diff)} na semana` });
      else change = node('span', { className: 'fuel-change', text: 'mesmo preço da semana passada' });
    }
    return node('li', {}, change ? [name, price, change] : [name, price]);
  });

  el('board-list').replaceChildren(...items);
}

function renderVerdict(city) {
  const gas = city.prices.gasolina;
  const eth = city.prices.etanol;
  const g = gas && gas[gas.length - 1];
  const e = eth && eth.find((p) => g && p[0] === g[0]);

  if (!g || !e) {
    el('verdict-answer').textContent = 'Sem dados pra comparar';
    el('verdict-detail').textContent = `A ANP não pesquisou os dois combustíveis em ${city.name} na mesma semana.`;
    return;
  }

  const ratio = e[1] / g[1];
  const pct = Math.round(ratio * 100);
  el('verdict-answer').textContent = ratio <= ETANOL_LIMIT ? 'Vai de etanol' : 'Vai de gasolina';
  el('verdict-detail').textContent =
    `O etanol está custando ${pct}% do preço da gasolina (R$ ${money(e[1])} contra R$ ${money(g[1])}). ` +
    'Como o carro flex roda menos com etanol, ele costuma valer a pena só até uns 70%.';
}

function renderChart(city) {
  const box = el('chart');
  const points = city.prices[current.product];
  const label = meta.products[current.product].label;

  if (!points || points.length < 2) {
    box.replaceChildren(node('p', { className: 'chart-empty', text: `Não tem histórico de ${label.toLowerCase()} suficiente pra essa cidade.` }));
    return;
  }

  // desenha na largura real pro texto nao encolher no celular
  const W = Math.round(Math.min(Math.max(box.clientWidth || 640, 300), 720));
  const narrow = W < 480;
  const H = narrow ? 220 : 260, left = 44, right = 12, top = 30, bottom = 30;
  const weeks = meta.weeks.length;
  const scale = niceScale(Math.min(...points.map((p) => p[2])), Math.max(...points.map((p) => p[3])));
  const yMin = scale.min, yMax = scale.max;

  const x = (week) => left + (week / Math.max(weeks - 1, 1)) * (W - left - right);
  const y = (value) => top + (1 - (value - yMin) / (yMax - yMin)) * (H - top - bottom);

  const chart = svg('svg', { viewBox: `0 0 ${W} ${H}`, role: 'img', 'aria-label': `${label} em ${city.name}: de R$ ${money(points[0][1])} para R$ ${money(points[points.length - 1][1])}` });

  for (const value of scale.ticks) {
    chart.append(svg('line', { class: 'grid', x1: left, x2: W - right, y1: y(value), y2: y(value) }));
    chart.append(svg('text', { class: 'axis', x: left - 6, y: y(value) + 4, 'text-anchor': 'end' }, money(value)));
  }

  const step = narrow ? 3 : weeks > 8 ? 2 : 1;
  for (let i = 0; i < weeks; i += step) {
    chart.append(svg('text', { class: 'axis', x: x(i), y: H - 8, 'text-anchor': 'middle' }, shortDate(meta.weeks[i])));
  }

  const band = points.map((p) => `${x(p[0])},${y(p[3])}`).concat([...points].reverse().map((p) => `${x(p[0])},${y(p[2])}`));
  chart.append(svg('polygon', { class: 'band', points: band.join(' ') }));
  chart.append(svg('polyline', { class: 'avg', points: points.map((p) => `${x(p[0])},${y(p[1])}`).join(' ') }));
  for (const p of points) chart.append(svg('circle', { class: 'dot', cx: x(p[0]), cy: y(p[1]), r: 3 }));

  const cursor = svg('line', { class: 'cursor', y1: top, y2: H - bottom, visibility: 'hidden' });
  const readout = svg('text', { class: 'readout', x: left, y: 16 });
  chart.append(cursor, readout);

  const showPoint = (p) => {
    cursor.setAttribute('x1', x(p[0]));
    cursor.setAttribute('x2', x(p[0]));
    cursor.setAttribute('visibility', 'visible');
    const when = shortDate(meta.weeks[p[0]]);
    readout.textContent = narrow
      ? `${when}: R$ ${money(p[1])} (${money(p[2])} a ${money(p[3])})`
      : `Semana até ${when}: R$ ${money(p[1])} (de ${money(p[2])} a ${money(p[3])})`;
  };
  showPoint(points[points.length - 1]);

  chart.addEventListener('pointermove', (event) => {
    const rect = chart.getBoundingClientRect();
    const px = ((event.clientX - rect.left) / rect.width) * W;
    const nearest = points.reduce((a, b) => (Math.abs(x(b[0]) - px) < Math.abs(x(a[0]) - px) ? b : a));
    showPoint(nearest);
  });
  chart.addEventListener('pointerleave', () => showPoint(points[points.length - 1]));

  box.replaceChildren(chart);
}

function renderRanking(state, city) {
  const latest = meta.weeks.length - 1;
  const label = meta.products[current.product].label;

  const rows = state.cities
    .map((c) => ({ city: c, point: (c.prices[current.product] || []).find((p) => p[0] === latest) }))
    .filter((r) => r.point)
    .sort((a, b) => a.point[1] - b.point[1]);

  el('ranking-title').textContent = `${label} mais barato em ${state.name}`;

  const position = rows.findIndex((r) => r.city.slug === city.slug);
  const body = rows.slice(0, RANKING_SIZE).map((r) => {
    const tr = node('tr', r.city.slug === city.slug ? { className: 'current' } : {}, [
      node('td', { text: r.city.name }),
      node('td', { className: 'num', text: `R$ ${money(r.point[1])}` }),
      node('td', { className: 'num', text: `${r.point[4]}` }),
    ]);
    return tr;
  });

  if (!rows.length) {
    body.push(node('tr', {}, [node('td', { colspan: '3', text: 'Nenhuma cidade do estado foi pesquisada nessa semana.' })]));
  }
  el('ranking-body').replaceChildren(...body);

  let note = '';
  if (position >= RANKING_SIZE) note = `${city.name} aparece em ${position + 1}º de ${rows.length} cidades pesquisadas.`;
  else if (position === -1 && rows.length) note = `${city.name} não teve pesquisa desse combustível na última semana.`;
  el('ranking-note').textContent = note;
}

async function render() {
  const state = await loadState(current.uf);
  const city = state.cities.find((c) => c.slug === current.city) || state.cities[0];
  current.city = city.slug;

  fillCities(state);
  renderBoard(city);
  renderVerdict(city);
  renderChart(city);
  renderRanking(state, city);
  writeUrl();
}

async function safeRender() {
  try {
    el('content').hidden = false;
    await render();
    el('status').hidden = true;
  } catch (err) {
    el('content').hidden = true;
    el('status').textContent = 'Não foi possível carregar os dados agora. Tenta recarregar a página.';
    el('status').hidden = false;
    console.error(err);
  }
}

async function start() {
  try {
    meta = await getJson('data/meta.json');
  } catch (err) {
    el('status').textContent = 'Não foi possível carregar os dados agora. Tenta recarregar a página.';
    console.error(err);
    return;
  }

  const wanted = readUrl();
  current.uf = meta.states.some((s) => s.uf === wanted.uf) ? wanted.uf : DEFAULT_UF;
  current.city = /^[a-z0-9-]{1,80}$/.test(wanted.city) ? wanted.city : (current.uf === DEFAULT_UF ? DEFAULT_CITY : '');
  current.product = CHART_PRODUCTS.includes(wanted.product) ? wanted.product : 'gasolina';

  const updated = new Date(meta.updated_at);
  if (!Number.isNaN(updated.getTime())) {
    el('updated').textContent = `Atualizado em ${updated.toLocaleDateString('pt-BR')}.`;
  }

  fillStates();
  fillProducts();

  el('state').addEventListener('change', (e) => {
    current.uf = e.target.value;
    current.city = '';
    safeRender();
  });
  el('city').addEventListener('change', (e) => {
    current.city = e.target.value;
    safeRender();
  });
  el('product').addEventListener('change', (e) => {
    current.product = e.target.value;
    safeRender();
  });

  let resizeTimer;
  let lastWidth = window.innerWidth;
  window.addEventListener('resize', () => {
    if (window.innerWidth === lastWidth) return;
    lastWidth = window.innerWidth;
    clearTimeout(resizeTimer);
    resizeTimer = setTimeout(safeRender, 200);
  });

  safeRender();
}

start();

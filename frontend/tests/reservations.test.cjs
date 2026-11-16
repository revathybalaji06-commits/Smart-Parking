// Run with: node --test frontend/tests/reservations.test.cjs
const { test } = require('node:test');
const assert = require('node:assert/strict');
const vm = require('node:vm');
const fs = require('node:fs');
const source = fs.readFileSync(require('node:path').join(__dirname, '../index.html'), 'utf8').split('<script>')[1].split('</script>')[0];

function app(initial = {}, data = {}) {
  const storage = new Map(Object.entries(initial));
  const elements = new Map();
  const element = () => ({ children: [], hidden: false, textContent: '', value: '',
    append(child) { this.children.push(child); }, replaceChildren() { this.children = []; },
    setAttribute() {}, querySelector() { return this.button ||= element(); } });
  const get = (id) => { if (!elements.has(id)) elements.set(id, element()); return elements.get(id); };
  const requests = [];
  const context = vm.createContext({
    document: { getElementById: get, createElement: element },
    localStorage: { getItem: (k) => storage.get(k) ?? null, setItem: (k,v) => storage.set(k,String(v)), removeItem: (k) => storage.delete(k) },
    navigator: {}, setInterval() {}, clearInterval() {},
    fetch: async (path, options) => {
      requests.push([path, options]);
      if (path === '/layout') return new Promise(() => {}); // Start explicitly in each test.
      if (data[path] instanceof Error) throw data[path];
      const result = data[path];
      return { ok: result !== undefined, status: result === undefined ? 404 : 200,
        json: async () => result ?? { message: 'Not found' } };
    },
  });
  vm.runInContext(source, context);
  return { storage, get, requests, run: (code) => vm.runInContext(code, context) };
}
const vehicle = (id, status = 'reserved') => ({ reservation_id: id, slot_id: id, plate: `TN${id}`, label: `S${id}`, status: 'active', slot_status: status });
const layout = { nodes: { ENTRY: [0,0], EXIT: [10,10] }, edges: [], trees: [], buildings: [], width: 20, height: 20 };
const route = { points: [[0,0],[1,1]], distances: [0,2], steps: [{text: 'Drive', distance: 2}] };
function dataFor(...vehicles) {
  const data = { '/availability': { lot: {free: 10, max: 20}, classes: [] }, '/slots': [] };
  for (const r of vehicles) { data[`/reservations/${r.reservation_id}`] = r; data[`/reservations/${r.reservation_id}/route`] = route; }
  return data;
}

test('legacy reservation migrates and refresh restores multiple vehicles with entry form visible', async () => {
  const app1 = app({ reservationId: '1', reservationIds: '["2"]' }, dataFor(vehicle(1), vehicle(2)));
  app1.run(`layout = ${JSON.stringify(layout)}`);
  await app1.run('refresh()');
  assert.equal(app1.run('reservations.length'), 2);
  assert.equal(app1.get('reserveForm').hidden, false);
  assert.deepEqual(JSON.parse(app1.storage.get('reservationIds')), ['2', '1']);
  assert.equal(app1.storage.has('reservationId'), false);
  const app2 = app(Object.fromEntries(app1.storage), dataFor(vehicle(1), vehicle(2)));
  await app2.run('loadReservations()');
  assert.deepEqual(JSON.parse(app2.storage.get('reservationIds')), ['2', '1']);
});

test('finished and missing reservations are removed without removing other vehicles', async () => {
  const a = app({ reservationIds: '[1,2,3,4]' }, { ...dataFor(vehicle(1)), '/reservations/2': {...vehicle(2), status: 'completed'}, '/reservations/3': {...vehicle(3), status: 'expired'} });
  await a.run('loadReservations()');
  assert.deepEqual(JSON.parse(a.storage.get('reservationIds')), ['1']);
});

test('network failure preserves IDs for retry', async () => {
  const a = app({reservationIds: '[1,2]'}, {...dataFor(vehicle(1)), '/reservations/2': new Error('offline')});
  await assert.rejects(a.run('loadReservations()'));
  assert.equal(a.storage.get('reservationIds'), '[1,2]');
});

test('selecting another vehicle resets guidance and loads that vehicle route', async () => {
  const a = app({reservationIds: '[1,2]'}, dataFor(vehicle(1), vehicle(2)));
  a.run(`layout = ${JSON.stringify(layout)}`);
  await a.run('refresh()');
  a.run('travelled = 1; selectedId = "2"');
  await a.run('refresh()');
  assert.equal(a.run('reservation.reservation_id'), 2);
  assert.equal(a.run('travelled'), 0);
  assert.equal(a.storage.get('selectedReservationId'), '2');
  assert.ok(a.requests.some(([p]) => p === '/reservations/2/route'));
});

test('each vehicle button targets its own reservation, including a nonselected vehicle', async () => {
  const a = app({reservationIds: '[1,2]'}, {...dataFor(vehicle(1), vehicle(2,'occupied')), '/reservations/2/depart': {}});
  a.run(`layout = ${JSON.stringify(layout)}`);
  await a.run('refresh()');
  const second = a.get('vehicles').children[1];
  await second.children.find((b) => b.textContent === 'I am leaving').onclick();
  assert.ok(a.requests.some(([p, opts]) => p === '/reservations/2/depart' && opts.method === 'POST'));
  assert.equal(a.run('reservation.reservation_id'), 1);
});

test('adding another vehicle retains the first and selects the new one', async () => {
  const a = app({reservationIds: '[1]'}, {...dataFor(vehicle(1), vehicle(2)), '/reserve': vehicle(2)});
  a.run(`layout = ${JSON.stringify(layout)}`);
  await a.run('refresh()');
  a.get('plate').value = 'TN2'; a.get('vehicleClass').value = '2';
  a.get('reserveForm').onsubmit({preventDefault(){}});
  // Wait for the submitted action and its queued reload to settle.
  await new Promise(setImmediate);
  assert.deepEqual(JSON.parse(a.storage.get('reservationIds')), ['1', '2']);
  assert.equal(a.run('reservation.reservation_id'), 2);
  assert.equal(a.get('reserveForm').hidden, false);
});

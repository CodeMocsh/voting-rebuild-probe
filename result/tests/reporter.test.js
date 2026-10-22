const test = require('node:test');
const assert = require('node:assert');
const { createReporter } = require('../src/reporter');

class Stop extends Error {}

function harness({ connect, stopAfterWaits }) {
  const broadcasts = [];
  const logs = { log: [], error: [] };
  const waits = [];
  const reporter = createReporter({
    connect,
    broadcast: (event, payload) => broadcasts.push([event, payload]),
    log: { log: (m) => logs.log.push(m), error: (m) => logs.error.push(m) },
    wait: async (ms) => {
      waits.push(ms);
      if (waits.length >= stopAfterWaits) throw new Stop();
    },
  });
  return { reporter, broadcasts, logs, waits };
}

const clientOf = (query) => async () => ({ query });

test('greets the one socket only', () => {
  const { reporter, broadcasts } = harness({ connect: clientOf(), stopAfterWaits: 1 });
  const emitted = [];
  reporter.greet({ emit: (...args) => emitted.push(args) });
  assert.deepStrictEqual(emitted, [['message', { text: 'Welcome!' }]]);
  assert.deepStrictEqual(broadcasts, []);
});

test('broadcasts scores to all and defaults to 0', async () => {
  const { reporter, broadcasts, logs, waits } = harness({
    connect: clientOf(async () => ({ rows: [{ vote: 'b', count: '3' }] })),
    stopAfterWaits: 2,
  });
  await assert.rejects(reporter.start(), Stop);
  assert.deepStrictEqual(broadcasts, [
    ['scores', '{"a":0,"b":3}'],
    ['scores', '{"a":0,"b":3}'],
  ]);
  assert.deepStrictEqual(logs.log, ['Connected to db']);
  assert.deepStrictEqual(waits, [1000, 1000]);
});

test('a count error is logged, sends nothing and the loop goes on', async () => {
  let calls = 0;
  const { reporter, broadcasts, logs } = harness({
    connect: clientOf(async () => {
      calls++;
      if (calls === 1) throw new Error('boom');
      return { rows: [{ vote: 'a', count: '1' }] };
    }),
    stopAfterWaits: 2,
  });
  await assert.rejects(reporter.start(), Stop);
  assert.deepStrictEqual(logs.error, ['Error performing query: Error: boom']);
  assert.deepStrictEqual(broadcasts, [['scores', '{"a":1,"b":0}']]);
});

test('retries 1000 times, one second apart, then gives up', async () => {
  let tries = 0;
  const { reporter, logs, waits, broadcasts } = harness({
    connect: async () => {
      tries++;
      throw new Error('down');
    },
    stopAfterWaits: Infinity,
  });
  await reporter.start();
  assert.strictEqual(tries, 1000);
  assert.strictEqual(waits.length, 999);
  assert.strictEqual(logs.error.filter((m) => m === 'Waiting for db').length, 1000);
  assert.strictEqual(logs.error[1000], 'Giving up');
  assert.deepStrictEqual(broadcasts, []);
});

test('connects after some failures', async () => {
  let tries = 0;
  const { reporter, logs } = harness({
    connect: async () => {
      tries++;
      if (tries < 3) throw new Error('down');
      return { query: async () => ({ rows: [] }) };
    },
    stopAfterWaits: 3,
  });
  await assert.rejects(reporter.start(), Stop);
  assert.strictEqual(tries, 3);
  assert.deepStrictEqual(logs.log, ['Connected to db']);
});

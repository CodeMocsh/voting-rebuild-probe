const fs = require('node:fs');
const path = require('node:path');
const vm = require('node:vm');
const { createReporter } = require('../src/reporter');

class Stop extends Error {}

function pageFor(emitted) {
  const handlers = {};
  const scope = { $apply: (fn) => fn() };
  const sandbox = {
    angular: {
      module: () => ({ controller: (name, fn) => fn(scope) }),
    },
    io: { connect: () => ({ on: (event, handler) => (handlers[event] = handler) }) },
    document: { getElementById: () => ({ style: {} }), body: { style: {} } },
  };
  const source = fs.readFileSync(path.join(__dirname, '..', 'views', 'app.js'), 'utf8');
  vm.runInNewContext(source, sandbox);
  return {
    scope,
    receive: (event, payload) => handlers[event](payload),
  };
}

function countRows(votes) {
  const counts = {};
  votes.forEach((option) => {
    counts[option] = (counts[option] || 0) + 1;
  });
  return Object.entries(counts).map(([vote, count]) => ({ vote, count: String(count) }));
}

async function run({ votes, unreachable }) {
  const out = {};
  const errors = [];
  const scoresSent = [];
  const reporter = createReporter({
    connect: async () => {
      if (unreachable) throw new Error('the votes are unreachable');
      return { query: async () => ({ rows: countRows(votes) }) };
    },
    broadcast: (event, payload) => scoresSent.push([event, payload]),
    log: { log: () => {}, error: (msg) => errors.push(msg) },
    wait: async () => {
      if (!unreachable) throw new Stop();
    },
  });
  const page = pageFor();
  reporter.greet({
    emit: (event, payload) => {
      out.greeting = payload.text;
      page.receive(event, payload);
    },
  });
  try {
    await reporter.start();
  } catch (error) {
    if (!(error instanceof Stop)) throw error;
  }
  scoresSent.forEach(([event, payload]) => {
    out.scores = typeof payload === "string" ? JSON.parse(payload) : payload;
    page.receive(event, payload);
  });
  out.a_percent = page.scope.aPercent;
  out.b_percent = page.scope.bPercent;
  out.total = page.scope.total;
  const queryErrors = errors.filter((msg) => msg.startsWith('Error performing query'));
  out.query_error_log = queryErrors.length > 0 ? queryErrors.join('\n') : undefined;
  return out;
}

let input = '';
process.stdin.on('data', (chunk) => (input += chunk));
process.stdin.on('end', async () => {
  const out = await run(JSON.parse(input));
  process.stdout.write(JSON.stringify(out));
});

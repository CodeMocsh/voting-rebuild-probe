const test = require('node:test');
const assert = require('node:assert');
const { readConfig } = require('../src/config');

const full = {
  PGHOST: 'db',
  PGPORT: '5432',
  PGUSER: 'u',
  PGPASSWORD: 'p',
  PGDATABASE: 'votes',
  PGSSL: 'true',
};

test('reads the connection settings', () => {
  assert.deepStrictEqual(readConfig(full), {
    host: 'db',
    port: 5432,
    user: 'u',
    password: 'p',
    database: 'votes',
    ssl: true,
  });
});

for (const name of Object.keys(full)) {
  test('refuses to start without ' + name, () => {
    const env = { ...full };
    delete env[name];
    assert.throws(() => readConfig(env), new RegExp(name));
  });
}

test('refuses a PGSSL that is not true or false', () => {
  assert.throws(() => readConfig({ ...full, PGSSL: 'yes' }), /PGSSL/);
});

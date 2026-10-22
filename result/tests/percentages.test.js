const test = require('node:test');
const assert = require('node:assert');
const fs = require('node:fs');
const path = require('node:path');
const vm = require('node:vm');

const source = fs.readFileSync(path.join(__dirname, '..', 'views', 'app.js'), 'utf8');
const sandbox = {
  angular: { module: () => ({ controller: () => {} }) },
  io: { connect: () => ({ on: () => {} }) },
  document: { getElementById: () => ({ style: {} }), body: { style: {} } },
};
vm.runInNewContext(source, sandbox);
const getPercentages = vm.runInNewContext('getPercentages', sandbox);

test('23 and 17 give 57 and 43', () => {
  assert.deepStrictEqual({ ...getPercentages(23, 17) }, { a: 57, b: 43 });
});

test('29 and 171 give 14 and 86', () => {
  assert.deepStrictEqual({ ...getPercentages(29, 171) }, { a: 14, b: 86 });
});

test('no votes give 50 and 50', () => {
  assert.deepStrictEqual({ ...getPercentages(0, 0) }, { a: 50, b: 50 });
});

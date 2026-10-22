const REQUIRED = ['PGHOST', 'PGPORT', 'PGUSER', 'PGPASSWORD', 'PGDATABASE', 'PGSSL'];

function readConfig(env) {
  const missing = REQUIRED.filter((name) => env[name] === undefined);
  if (missing.length > 0) {
    throw new Error('Missing environment variables: ' + missing.join(', '));
  }
  if (env.PGSSL !== 'true' && env.PGSSL !== 'false') {
    throw new Error('PGSSL must be true or false');
  }
  return {
    host: env.PGHOST,
    port: Number(env.PGPORT),
    user: env.PGUSER,
    password: env.PGPASSWORD,
    database: env.PGDATABASE,
    ssl: env.PGSSL === 'true',
  };
}

module.exports = { readConfig };

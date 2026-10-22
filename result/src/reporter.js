const CONNECT_TRIES = 1000;
const INTERVAL_MS = 1000;
const COUNT_SQL = 'SELECT vote, COUNT(id) AS count FROM votes GROUP BY vote';

function collectVotes(result) {
  const votes = { a: 0, b: 0 };
  result.rows.forEach((row) => {
    votes[row.vote] = parseInt(row.count);
  });
  return votes;
}

function createReporter({ connect, broadcast, log, wait }) {
  async function connectWithRetry() {
    for (let attempt = 1; attempt <= CONNECT_TRIES; attempt++) {
      try {
        return await connect();
      } catch (error) {
        log.error('Waiting for db');
        if (attempt < CONNECT_TRIES) {
          await wait(INTERVAL_MS);
        }
      }
    }
    return null;
  }

  async function tally(client) {
    try {
      const result = await client.query(COUNT_SQL, []);
      broadcast('scores', JSON.stringify(collectVotes(result)));
    } catch (error) {
      log.error('Error performing query: ' + error);
    }
  }

  async function start() {
    const client = await connectWithRetry();
    if (client === null) {
      log.error('Giving up');
      return;
    }
    log.log('Connected to db');
    for (;;) {
      await tally(client);
      await wait(INTERVAL_MS);
    }
  }

  function greet(socket) {
    socket.emit('message', { text: 'Welcome!' });
  }

  return { start, greet };
}

module.exports = { createReporter };

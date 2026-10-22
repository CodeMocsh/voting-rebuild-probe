const express = require('express');
const cookieParser = require('cookie-parser');
const { Pool } = require('pg');
const http = require('http');
const { readConfig } = require('./src/config');
const { createReporter } = require('./src/reporter');

const port = process.env.PORT || 4000;
const pool = new Pool(readConfig(process.env));
const app = express();
const server = http.Server(app);
const io = require('socket.io')(server);

const reporter = createReporter({
  connect: () => pool.connect(),
  broadcast: (event, payload) => io.sockets.emit(event, payload),
  log: { log: (msg) => console.log(msg), error: (msg) => console.error(msg) },
  wait: (ms) => new Promise((resolve) => setTimeout(resolve, ms)),
});

io.on('connection', (socket) => {
  reporter.greet(socket);
  socket.on('subscribe', (data) => {
    socket.join(data.channel);
  });
});

app.use(cookieParser());
app.use(express.urlencoded({ extended: true }));
app.use(express.static(__dirname + '/views'));

server.listen(port, () => {
  console.log('App running on port ' + server.address().port);
});

reporter.start();

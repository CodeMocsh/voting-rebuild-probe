FROM node:18-slim
WORKDIR /usr/local/app
COPY package*.json ./
RUN npm install
COPY . .
CMD ["node", "server.js"]

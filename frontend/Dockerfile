FROM node:24-slim
WORKDIR /app
COPY package.json package-lock.json* pnpm-lock.yaml* yarn.lock* ./
RUN npm ci
COPY --chown=node:node . .
RUN chown -R node:node /app
ENV PORT=3000 HOSTNAME=0.0.0.0
USER node
HEALTHCHECK --interval=30s --timeout=5s --start-period=30s --retries=3 \
  CMD node -e "const http = require('http'); const req = http.get({ host: '127.0.0.1', port: process.env.PORT || 3000, path: '/' }, (res) => process.exit(res.statusCode < 500 ? 0 : 1)); req.on('error', () => process.exit(1)); req.setTimeout(5000, () => { req.destroy(); process.exit(1); });"
EXPOSE 3000
CMD ["npm", "run", "dev", "--", "-H", "0.0.0.0"]

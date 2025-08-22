FROM node:22-slim
WORKDIR /app
COPY package.json package-lock.json* pnpm-lock.yaml* yarn.lock* ./
RUN npm install -g npm@latest && npm install
COPY . .
ENV PORT=3000 HOSTNAME=0.0.0.0
EXPOSE 3000
CMD ["npx","next","dev"]

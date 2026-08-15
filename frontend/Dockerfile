FROM node:22-alpine

WORKDIR /app

COPY package.json package-lock.json ./
RUN npm ci

COPY . .

# Dev server — docker-compose wires VITE_API_URL at it so the dashboard
# reads the live API. The public deployment is a static `npm run build`
# instead, with no API behind it (see README).
EXPOSE 5173
CMD ["npm", "run", "dev", "--", "--host", "0.0.0.0"]

FROM node:20-alpine

WORKDIR /app

COPY package.json ./
RUN npm install

COPY . .

# VITE_API_URL is baked in at build time (Vite inlines env vars).
# On Railway, set it as a service variable so the build picks it up.
ARG VITE_API_URL
ENV VITE_API_URL=$VITE_API_URL
RUN npm run build

# Railway injects PORT; the preview script binds to it.
ENV PORT=4173
EXPOSE 4173

CMD ["npm", "run", "preview"]

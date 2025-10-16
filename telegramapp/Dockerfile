FROM node:18-alpine as build
WORKDIR /app
COPY . .
RUN npm install
RUN npm run build
# Вот здесь!
RUN echo "=== BUILD DIR ===" && ls -l /app/build || true
RUN echo "=== APP DIR ===" && ls -l /app || true
RUN echo "=== BUILD FILES ===" && find /app/build || true

FROM nginx:1.25-alpine

# Install wget for healthcheck
RUN apk add --no-cache wget

RUN mkdir -p /usr/share/nginx/html/podbortg
COPY --from=build /app/build/ /usr/share/nginx/html/podbortg/
COPY --from=build /app/public/health /usr/share/nginx/html/health
COPY nginx.conf /etc/nginx/conf.d/default.conf
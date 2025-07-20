FROM node:20-alpine AS build
WORKDIR /app
COPY . .
RUN npm install && npm run build

FROM nginx:1.25-alpine
RUN mkdir -p /usr/share/nginx/html/podbortg
COPY --from=build /app/build/ /usr/share/nginx/html/podbortg/
EXPOSE 80
CMD ["nginx", "-g", "daemon off;"] 
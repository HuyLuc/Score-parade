FROM node:18-alpine AS build
WORKDIR /app

# Cài đặt deps
COPY frontend/package*.json ./
RUN npm install

# Build với biến môi trường API
ARG REACT_APP_API_URL=http://localhost:8000
ENV REACT_APP_API_URL=${REACT_APP_API_URL}
COPY frontend /app
RUN npm run build

FROM nginx:stable-alpine
COPY --from=build /app/build /usr/share/nginx/html
EXPOSE 80
CMD ["nginx", "-g", "daemon off;"]


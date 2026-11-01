# ЭТАП 1: Сборка приложения - используем Node.js 20
FROM node:20-alpine AS build

WORKDIR /app

# Копируем package.json и устанавливаем зависимости
COPY package*.json ./
RUN npm install

# Адрес API, зашиваемый в сборку (Vite подставляет его на этапе build). Пусто — http://localhost:8000
ARG VITE_API_BASE_URL=
ENV VITE_API_BASE_URL=$VITE_API_BASE_URL

# Копируем исходный код и собираем проект
COPY . .
RUN npm run build

# ЭТАП 2: Запуск через Nginx
FROM nginx:alpine

# Копируем собранные файлы из первого этапа
COPY --from=build /app/dist /usr/share/nginx/html

# Копируем конфигурацию Nginx
COPY nginx.conf /etc/nginx/conf.d/default.conf

EXPOSE 80

CMD ["nginx", "-g", "daemon off;"]
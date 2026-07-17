FROM node:22-alpine AS base
WORKDIR /app
COPY package.json package-lock.json ./

# --- dev target: deps only, source bind-mounted at runtime ---
FROM base AS dev
RUN npm ci
CMD ["npm", "run", "dev", "--", "--host"]

# --- build stage: full build for the prod image ---
FROM base AS build
RUN npm ci
COPY . .
RUN npm run build

# --- prod target: static assets served by nginx ---
FROM nginx:alpine AS prod
COPY --from=build /app/dist /usr/share/nginx/html
COPY nginx.conf /etc/nginx/conf.d/default.conf
EXPOSE 80
CMD ["nginx", "-g", "daemon off;"]

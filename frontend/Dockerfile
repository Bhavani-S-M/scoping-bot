# -------------------------------
# Stage 1: Build React app
# -------------------------------
FROM node:18-alpine AS builder

WORKDIR /app

# Install dependencies efficiently
COPY package*.json ./
RUN npm ci --silent

# Copy source and build
COPY . .
RUN npm run build


# -------------------------------
# Stage 2: Serve static build with Nginx
# -------------------------------
FROM nginx:alpine

# Clean existing Nginx content
RUN rm -rf /usr/share/nginx/html/*

# Copy React build output
COPY --from=builder /app/dist /usr/share/nginx/html

# Custom Nginx config to handle SPA routing and .mjs MIME
RUN echo 'server {\n\
    listen 80;\n\
    server_name _;\n\
    root /usr/share/nginx/html;\n\
    index index.html;\n\
    include /etc/nginx/mime.types;\n\
\n\
    # SPA routing fix (main part)\n\
    location / {\n\
        try_files $uri /index.html;\n\
    }\n\
\n\
    # Fix MIME for modern JS modules (.mjs)\n\
    location ~* \.(mjs|js)$ {\n\
        add_header Content-Type application/javascript;\n\
    }\n\
}' > /etc/nginx/conf.d/default.conf

# Expose Nginx port
EXPOSE 80

CMD ["nginx", "-g", "daemon off;"]


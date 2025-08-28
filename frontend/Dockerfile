# Usar imagen base de nginx
FROM nginx:alpine

# Copiar archivos estáticos del frontend
COPY static/ /usr/share/nginx/html/

# Copiar configuración personalizada de nginx
COPY nginx.conf /etc/nginx/conf.d/default.conf

# Exponer puerto 80
EXPOSE 80

# Nginx se ejecuta automáticamente

#frontend
FROM nginx:stable-alpine

WORKDIR /usr/share/nginx/html

COPY ./static /usr/share/nginx/html/static
COPY ./templates /usr/share/nginx/html
COPY nginx.conf /etc/nginx/nginx.conf

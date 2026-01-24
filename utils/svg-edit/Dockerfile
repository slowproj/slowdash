FROM node:20-alpine as build

WORKDIR /app
RUN apk add --no-cache git
RUN git clone https://github.com/SVG-Edit/svgedit

RUN cd svgedit && npm i && npm run build --workspace @svgedit/svgcanvas && npm run build

#WORKDIR /app/svgedit
#EXPOSE 8000
#CMD ["npm", "run", "start"]


#######
FROM nginx:alpine AS prod

COPY --from=build /app/svgedit/dist/editor /usr/share/nginx/html/app

RUN echo '<a href="app/index.html">SVG-Edit App</a>'  > /usr/share/nginx/html/index.html

EXPOSE 80
CMD ["nginx", "-g", "daemon off;"]

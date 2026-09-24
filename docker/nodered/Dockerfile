FROM nodered/node-red:4.0.9-22
USER root
RUN apk add --no-cache git
USER node-red
WORKDIR /usr/src/node-red
RUN npm install --omit=dev --no-audit --no-fund \
    node-red-contrib-home-assistant@0.73.2

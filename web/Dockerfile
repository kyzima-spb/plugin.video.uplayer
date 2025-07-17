FROM node:20.17-bookworm-slim AS development

RUN apt-get update && apt-get install -y --no-install-recommends iputils-ping
USER node

WORKDIR /app

RUN --mount=type=cache,target=/home/node/.npm,uid=1000,gid=1000 \
    --mount=type=bind,source=./package.json,target=package.json \
    --mount=type=bind,source=./package-lock.json,target=package-lock.json \
    npm ci

COPY --chown=node ./ ./

CMD ["npm", "run", "dev", "--", "--host"]

FROM development AS build

RUN npm run build

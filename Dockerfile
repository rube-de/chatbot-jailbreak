FROM ghcr.io/foundry-rs/foundry:stable AS contracts-build
WORKDIR /contracts
COPY ./contracts /contracts
RUN forge build

FROM node:21-alpine3.19 AS frontend-build
WORKDIR /frontend
COPY ./frontend/yarn.lock ./frontend/package.json /frontend
COPY --from=contracts-build /contracts/out /contracts/out
RUN yarn install
COPY ./frontend /frontend
EXPOSE 5173
CMD ["yarn", "dev", "--host", "0.0.0.0"]

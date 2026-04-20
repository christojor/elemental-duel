FROM golang:1.22-alpine AS builder
WORKDIR /app

RUN apk add --no-cache git

COPY . .
RUN go mod tidy
RUN CGO_ENABLED=0 GOOS=linux go build -o /tmp/battle-api .

FROM alpine:3.20
WORKDIR /app
RUN adduser -D duel
COPY --from=builder /tmp/battle-api ./battle-api

EXPOSE 8080
USER duel
CMD ["./battle-api"]

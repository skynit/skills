FROM alpine:3.19
WORKDIR /app
COPY server /app/server
COPY zoneinfo.zip /app/zoneinfo.zip
COPY ca-certificates.crt /etc/ssl/certs/ca-certificates.crt
ENV ZONEINFO=/app/zoneinfo.zip
EXPOSE 8088
CMD ["/app/server"]

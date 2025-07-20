FROM debian:stable-slim
RUN apt-get update && apt-get install -y curl cron && rm -rf /var/lib/apt/lists/*
COPY car-updater.sh /init-scripts/car-updater.sh
COPY crontab.txt /etc/cron.d/car-updater
RUN chmod +x /init-scripts/car-updater.sh && chmod 0644 /etc/cron.d/car-updater
RUN touch /var/log/car-updater.log
RUN crontab /etc/cron.d/car-updater
CMD ["cron", "-f"] 
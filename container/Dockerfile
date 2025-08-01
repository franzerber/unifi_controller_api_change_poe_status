FROM python:3-slim-bullseye

WORKDIR /usr/src/app

COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

COPY . .
RUN apt-get update && apt-get -y install cron

# Add crontab file in the cron directory
ADD cronfile.txt /etc/cron.d/unifi-cron
ADD main.py /usr/src/app/main.py
ADD settings.json /usr/src/app/settings.json

# Give execution rights on the cron job
RUN chmod 0644 /etc/cron.d/unifi-cron
RUN chmod +x /usr/src/app/main.py
# Set Timezone
ENV TZ=Europe/Berlin
RUN ln -snf /usr/share/zoneinfo/$TZ /etc/localtime && echo $TZ > /etc/timezone

# Apply cron job
RUN crontab /etc/cron.d/unifi-cron

CMD ["cron", "-f"]
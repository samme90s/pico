# Broker

## Setup

Create a password file:

```bash
touch broker/docker-compose.yml &&
touch broker/mosquitto.conf &&
touch broker/pwfile
```

Copy the following content into the `docker-compose.yml` file:

```yml
# docker-compose.yml
services:
  mosquitto:
    container_name: mosquitto
    image: eclipse-mosquitto:latest
    restart: unless-stopped
    ports:
      - 1883:1883
      - 9001:9001
    volumes:
      - ./mosquitto.conf:/mosquitto/config/mosquitto.conf
      - ./pwfile:/mosquitto/config/pwfile
    security_opt:
      - no-new-privileges:true
```

Copy the following content into the `mosquitto.conf` file:

```conf
; mosquitto.conf
allow_anonymous false
listener 1883
listener 9001
protocol websockets
password_file /mosquitto/config/pwfile
```

Run the broker:

```bash
docker compose -f broker/docker-compose.yml up -d --force-recreate
```

Fix `pwfile` permissions:

```bash
docker exec -it mosquitto chmod 0700 /mosquitto/config/pwfile &&
docker exec -it mosquitto chown root:root /mosquitto/config/pwfile
```

Add a user:

```bash
# It will ask for a password.
docker exec -it mosquitto mosquitto_passwd -c /mosquitto/config/pwfile {user} &&
docker restart mosquitto
```

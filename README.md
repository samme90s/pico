# Pico

**IMPORTANT** -- All commands are executed from the root directory of the project.

## Device

### Setup

```py
# src/config.py
#
# ******************** IMPORTANT! ********************
# *** This file should never be version controlled ***
# ****************************************************

# WiFi
SSID = ""
SSID_SECRET = ""

# Adafruit IO
ADA_USER = ""
ADA_SECRET = ""

# MQTT
HOST = "io.adafruit.com"
PORT = 1883
```

See [DEVICE.md](DEVICE.md) for more information.

## Mosquitto

### Setup

Create a password file:

```bash
touch broker/pwfile
```

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

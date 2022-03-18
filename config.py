from os import environ as env
import multiprocessing

PORT = int(env.get("PORT", 8080))
DEBUG_MODE = int(env.get("DEBUG_MODE", 1))
GOOGLE_APPLICATION_CREDENTIALS = "/Users/jacksonwittenberg/Desktop/secrets/starterkit-service-account.json" # WILL BE service_account.json stored insecret manangeer
GOOGLE_CLOUD_PROJECT = "starterkit-344119"

# Gunicorn config
bind = ":" + str(PORT)
workers = multiprocessing.cpu_count() * 2 + 1
threads = 2 * multiprocessing.cpu_count()
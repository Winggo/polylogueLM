import os
from dotenv import load_dotenv
from flask import Flask
from flask_cors import CORS
from flask_socketio import SocketIO

from src.redis_listener import start_redis_client, start_redis_pubsub
from src.db.firestore import start_firestore_project_client
from src.db.storage import start_storage_client


env = os.environ.get("FLASK_ENV", "local")
if env == "production":
    load_dotenv(".env.production")
elif env == "local":
    load_dotenv(".env.local")
else:
    load_dotenv(".env")


app = Flask(__name__)
CORS(app, supports_credentials=True, origins=[os.environ["CORS_ORIGIN"]])
socketio = SocketIO(app, cors_allowed_origins='*', transports=['websocket'])


ds_client = start_firestore_project_client(os.environ["GCP_PROJECT"])
app.config['FIRESTORE'] = ds_client

gcs_client = start_storage_client(os.environ["GCP_PROJECT"])
app.config['GCS'] = gcs_client
app.config['GCS_BUCKET'] = os.environ.get("GCS_BUCKET", "polylogue-canvas-images")


enable_redis = os.getenv("ENABLE_REDIS", "false").lower() == "true"
if enable_redis:
    r_client = start_redis_client()
    app.config['REDIS'] = r_client


enable_redis_pubsub = os.getenv("ENABLE_REDIS_PUBSUB", "false").lower() == "true"
if enable_redis_pubsub:
    pubsub = start_redis_pubsub(r_client, socketio)
    app.config['PUBSUB'] = pubsub

    from src.routes.sockets import socket_routes



from src.routes.datastore import ds_routes
app.register_blueprint(ds_routes, url_prefix="/ds")


from src.routes.api import api_routes
app.register_blueprint(api_routes, url_prefix="/api")


if __name__ == "__main__":
    socketio.run(app, debug=True)

import atexit
import json
import os
import secrets
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent
PID_PATH = BASE_DIR / "server.pid"
INSTANCE_TOKEN = secrets.token_urlsafe(24)
os.environ["APP_INSTANCE_TOKEN"] = INSTANCE_TOKEN


def remove_pid_file():
    try:
        identity = json.loads(PID_PATH.read_text(encoding="utf-8"))
        if identity.get("pid") == os.getpid():
            PID_PATH.unlink(missing_ok=True)
    except (OSError, ValueError, json.JSONDecodeError):
        pass


if __name__ == "__main__":
    from waitress import serve

    from main import FLASK_HOST, FLASK_PORT, app

    PID_PATH.write_text(
        json.dumps({"pid": os.getpid(), "instance_token": INSTANCE_TOKEN}),
        encoding="utf-8",
    )
    atexit.register(remove_pid_file)

    threads = int(os.getenv("WAITRESS_THREADS", "4"))
    print(f"Iniciando servidor de producao em http://{FLASK_HOST}:{FLASK_PORT}")
    try:
        serve(app, host=FLASK_HOST, port=FLASK_PORT, threads=threads)
    finally:
        remove_pid_file()

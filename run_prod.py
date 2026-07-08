import os

from waitress import serve

from main import FLASK_HOST, FLASK_PORT, app


if __name__ == "__main__":
    threads = int(os.getenv("WAITRESS_THREADS", "4"))
    print(f"Iniciando servidor de producao em http://{FLASK_HOST}:{FLASK_PORT}")
    serve(app, host=FLASK_HOST, port=FLASK_PORT, threads=threads)

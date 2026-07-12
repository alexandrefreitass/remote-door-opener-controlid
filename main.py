from flask import Flask, flash, jsonify, redirect, render_template, request, session, url_for
import hmac
import json
import os
import secrets
import sqlite3

import requests
from dotenv import load_dotenv


BASE_DIR = os.path.dirname(os.path.abspath(__file__))
CONFIG_PATH = os.path.join(BASE_DIR, "config.env")


def ensure_runtime_config():
    if os.path.exists(CONFIG_PATH):
        return

    secret_key = secrets.token_urlsafe(32)
    with open(CONFIG_PATH, "w", encoding="utf-8") as config_file:
        config_file.write(
            "\n".join(
                [
                    "# Configuracoes geradas automaticamente no primeiro uso",
                    "FLASK_HOST=0.0.0.0",
                    "FLASK_PORT=5000",
                    "FLASK_DEBUG=False",
                    f"SECRET_KEY={secret_key}",
                    "WAITRESS_THREADS=4",
                    "DATABASE_PATH=controlid_devices.db",
                    "",
                    "# O login administrativo sera criado na tela de configuracao inicial.",
                    "APP_USERNAME=",
                    "APP_PASSWORD=",
                    "",
                    "# Dados do equipamento podem ser cadastrados pela interface.",
                    "DEVICE_NAME=",
                    "DEVICE_LOCATION=",
                    "DEVICE_IP=",
                    "DEVICE_PORT=80",
                    "DEVICE_LOGIN=",
                    "DEVICE_PASSWORD=",
                    "DEVICE_ACTION_PARAMETERS=id=65793,reason=3",
                    "",
                ]
            )
        )


def write_config_values(values):
    existing = {}
    order = []

    if os.path.exists(CONFIG_PATH):
        with open(CONFIG_PATH, "r", encoding="utf-8", errors="ignore") as config_file:
            for line in config_file:
                stripped = line.strip()
                if not stripped or stripped.startswith("#") or "=" not in stripped:
                    continue
                key, value = stripped.split("=", 1)
                existing[key] = value
                order.append(key)

    for key, value in values.items():
        if key not in order:
            order.append(key)
        existing[key] = value
        os.environ[key] = value

    with open(CONFIG_PATH, "w", encoding="utf-8") as config_file:
        config_file.write("# Configuracoes da aplicacao\n")
        for key in order:
            config_file.write(f"{key}={existing.get(key, '')}\n")


ensure_runtime_config()
load_dotenv(CONFIG_PATH, override=True)

DATABASE_PATH = os.getenv("DATABASE_PATH", os.path.join(BASE_DIR, "controlid_devices.db"))
if not os.path.isabs(DATABASE_PATH):
    DATABASE_PATH = os.path.join(BASE_DIR, DATABASE_PATH)

app = Flask(__name__)
app.secret_key = os.getenv("SECRET_KEY") or secrets.token_urlsafe(32)

FLASK_HOST = os.getenv("FLASK_HOST", "0.0.0.0")
FLASK_PORT = int(os.getenv("FLASK_PORT", "5000"))
FLASK_DEBUG = os.getenv("FLASK_DEBUG", "False") == "True"
APP_USERNAME = os.getenv("APP_USERNAME", "").strip()
APP_PASSWORD = os.getenv("APP_PASSWORD", "")
APP_INSTANCE_TOKEN = os.getenv("APP_INSTANCE_TOKEN", "")


def auth_configured():
    return bool(APP_USERNAME and APP_PASSWORD)


@app.before_request
def require_login():
    public_endpoints = {"health", "login", "setup_admin", "static"}
    if request.endpoint in public_endpoints:
        return None

    if not auth_configured():
        return redirect(url_for("setup_admin"))

    if session.get("authenticated"):
        return None

    return redirect(url_for("login", next=request.full_path))


@app.route("/setup", methods=["GET", "POST"])
def setup_admin():
    global APP_PASSWORD, APP_USERNAME

    if auth_configured():
        return redirect(url_for("login"))

    if request.method == "POST":
        username = request.form.get("username", "").strip()
        password = request.form.get("password", "")
        confirm_password = request.form.get("confirm_password", "")

        if not username:
            flash("Informe um usuario administrador.", "error")
        elif len(password) < 6:
            flash("A senha deve ter pelo menos 6 caracteres.", "error")
        elif password != confirm_password:
            flash("A confirmacao de senha nao confere.", "error")
        else:
            APP_USERNAME = username
            APP_PASSWORD = password
            write_config_values(
                {
                    "APP_USERNAME": username,
                    "APP_PASSWORD": password,
                    "SECRET_KEY": os.getenv("SECRET_KEY") or secrets.token_urlsafe(32),
                }
            )
            session.clear()
            flash("Login administrativo criado. Entre para continuar.", "success")
            return redirect(url_for("login"))

    return render_template("setup.html")


@app.route("/login", methods=["GET", "POST"])
def login():
    if not auth_configured():
        return redirect(url_for("setup_admin"))

    if session.get("authenticated"):
        return redirect(url_for("index"))

    if request.method == "POST":
        username = request.form.get("username", "").strip()
        password = request.form.get("password", "")

        user_ok = hmac.compare_digest(username, APP_USERNAME)
        password_ok = hmac.compare_digest(password, APP_PASSWORD)

        if user_ok and password_ok:
            session.clear()
            session["authenticated"] = True
            session["username"] = username
            next_url = request.form.get("next") or url_for("index")
            if not next_url.startswith("/"):
                next_url = url_for("index")
            return redirect(next_url)

        flash("Usuario ou senha invalidos.", "error")

    return render_template("login.html", next_url=request.args.get("next", ""))


@app.route("/logout")
def logout():
    session.clear()
    flash("Sessao encerrada.", "success")
    return redirect(url_for("login"))


@app.route("/health")
def health():
    return jsonify(
        application="controle-de-acesso-controlid",
        instance_token=APP_INSTANCE_TOKEN,
        status="ok",
    )


def get_db():
    conn = sqlite3.connect(DATABASE_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    with get_db() as conn:
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS devices (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                location TEXT,
                device_ip TEXT NOT NULL,
                device_port INTEGER NOT NULL DEFAULT 80,
                device_login TEXT NOT NULL,
                device_password TEXT NOT NULL,
                action_parameters TEXT NOT NULL DEFAULT 'id=65793,reason=3',
                is_active INTEGER NOT NULL DEFAULT 0,
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
            )
            """
        )
        conn.commit()


def seed_from_env_if_empty():
    device_ip = os.getenv("DEVICE_IP")
    if not device_ip:
        return

    with get_db() as conn:
        total = conn.execute("SELECT COUNT(*) FROM devices").fetchone()[0]
        if total > 0:
            return

        conn.execute(
            """
            INSERT INTO devices (
                name,
                location,
                device_ip,
                device_port,
                device_login,
                device_password,
                action_parameters,
                is_active
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, 1)
            """,
            (
                os.getenv("DEVICE_NAME", "Porta Principal"),
                os.getenv("DEVICE_LOCATION", "Predio principal"),
                device_ip,
                int(os.getenv("DEVICE_PORT", "80")),
                os.getenv("DEVICE_LOGIN", "admin"),
                os.getenv("DEVICE_PASSWORD", ""),
                os.getenv("DEVICE_ACTION_PARAMETERS", "id=65793,reason=3"),
            ),
        )
        conn.commit()


def setup_app():
    init_db()
    seed_from_env_if_empty()


def list_devices():
    with get_db() as conn:
        return conn.execute(
            "SELECT * FROM devices ORDER BY is_active DESC, name COLLATE NOCASE"
        ).fetchall()


def get_device(device_id):
    with get_db() as conn:
        return conn.execute("SELECT * FROM devices WHERE id = ?", (device_id,)).fetchone()


def get_active_device():
    with get_db() as conn:
        return conn.execute(
            "SELECT * FROM devices WHERE is_active = 1 ORDER BY id LIMIT 1"
        ).fetchone()


def set_active_device(device_id):
    with get_db() as conn:
        conn.execute("UPDATE devices SET is_active = 0")
        conn.execute(
            "UPDATE devices SET is_active = 1, updated_at = CURRENT_TIMESTAMP WHERE id = ?",
            (device_id,),
        )
        conn.commit()


def parse_device_form():
    name = request.form.get("name", "").strip()
    location = request.form.get("location", "").strip()
    device_ip = request.form.get("device_ip", "").strip()
    device_login = request.form.get("device_login", "").strip()
    device_password = request.form.get("device_password", "").strip()
    action_parameters = request.form.get("action_parameters", "").strip()
    port_raw = request.form.get("device_port", "80").strip()

    if not name:
        raise ValueError("Informe um nome para o equipamento.")
    if not device_ip:
        raise ValueError("Informe o IP ou host do ControlID.")
    if not device_login:
        raise ValueError("Informe o login do equipamento.")
    if not device_password:
        raise ValueError("Informe a senha do equipamento.")

    try:
        device_port = int(port_raw)
    except ValueError as exc:
        raise ValueError("A porta deve ser um numero.") from exc

    if device_port < 1 or device_port > 65535:
        raise ValueError("A porta deve estar entre 1 e 65535.")

    if not action_parameters:
        action_parameters = "id=65793,reason=3"

    return {
        "name": name,
        "location": location,
        "device_ip": device_ip,
        "device_port": device_port,
        "device_login": device_login,
        "device_password": device_password,
        "action_parameters": action_parameters,
    }


def base_device_url(device):
    port = int(device["device_port"])
    host = device["device_ip"]
    if port == 80:
        return f"http://{host}"
    return f"http://{host}:{port}"


def open_door(device):
    base_url = base_device_url(device)
    login_url = f"{base_url}/login.fcgi"
    login_payload = {
        "login": device["device_login"],
        "password": device["device_password"],
    }

    response = requests.post(
        login_url,
        headers={"Content-Type": "application/json"},
        data=json.dumps(login_payload),
        timeout=5,
    )
    response.raise_for_status()

    session_id = response.json().get("session")
    if not session_id:
        raise ValueError("A resposta de login nao retornou uma sessao valida.")

    action_url = f"{base_url}/execute_actions.fcgi?session={session_id}"
    action_payload = {
        "actions": [
            {
                "action": "sec_box",
                "parameters": device["action_parameters"],
            }
        ]
    }

    action_response = requests.post(
        action_url,
        headers={"Content-Type": "application/json"},
        data=json.dumps(action_payload),
        timeout=5,
    )
    action_response.raise_for_status()
    return action_response.text


@app.route("/")
@app.route("/biometria")
def index():
    devices = list_devices()
    active_device = get_active_device()
    return render_template("index.html", devices=devices, active_device=active_device)


@app.route("/mostrar", methods=["POST"])
def mostrar():
    device = get_active_device()
    if not device:
        flash("Cadastre e ative um equipamento antes de abrir a porta.", "error")
        return redirect(url_for("configuracoes"))

    try:
        open_door(device)
        return render_template("sucesso.html", device=device)
    except (requests.exceptions.RequestException, json.JSONDecodeError, ValueError) as exc:
        print(f"Falha ao abrir porta: {exc}")
        return render_template("erro.html", device=device, error_detail=str(exc))


@app.route("/configuracoes")
def configuracoes():
    devices = list_devices()
    return render_template("configuracoes.html", devices=devices, editing_device=None)


@app.route("/configuracoes/<int:device_id>/editar")
def editar_configuracao(device_id):
    device = get_device(device_id)
    if not device:
        flash("Equipamento nao encontrado.", "error")
        return redirect(url_for("configuracoes"))

    devices = list_devices()
    return render_template("configuracoes.html", devices=devices, editing_device=device)


@app.route("/equipamentos", methods=["POST"])
def criar_equipamento():
    try:
        data = parse_device_form()
    except ValueError as exc:
        flash(str(exc), "error")
        return redirect(url_for("configuracoes"))

    with get_db() as conn:
        has_active = conn.execute(
            "SELECT COUNT(*) FROM devices WHERE is_active = 1"
        ).fetchone()[0]
        cursor = conn.execute(
            """
            INSERT INTO devices (
                name,
                location,
                device_ip,
                device_port,
                device_login,
                device_password,
                action_parameters,
                is_active
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                data["name"],
                data["location"],
                data["device_ip"],
                data["device_port"],
                data["device_login"],
                data["device_password"],
                data["action_parameters"],
                0 if has_active else 1,
            ),
        )
        conn.commit()
        new_id = cursor.lastrowid

    if request.form.get("activate") == "1":
        set_active_device(new_id)

    flash("Equipamento salvo com sucesso.", "success")
    return redirect(url_for("configuracoes"))


@app.route("/equipamentos/<int:device_id>/editar", methods=["POST"])
def atualizar_equipamento(device_id):
    if not get_device(device_id):
        flash("Equipamento nao encontrado.", "error")
        return redirect(url_for("configuracoes"))

    try:
        data = parse_device_form()
    except ValueError as exc:
        flash(str(exc), "error")
        return redirect(url_for("editar_configuracao", device_id=device_id))

    with get_db() as conn:
        conn.execute(
            """
            UPDATE devices
            SET name = ?,
                location = ?,
                device_ip = ?,
                device_port = ?,
                device_login = ?,
                device_password = ?,
                action_parameters = ?,
                updated_at = CURRENT_TIMESTAMP
            WHERE id = ?
            """,
            (
                data["name"],
                data["location"],
                data["device_ip"],
                data["device_port"],
                data["device_login"],
                data["device_password"],
                data["action_parameters"],
                device_id,
            ),
        )
        conn.commit()

    if request.form.get("activate") == "1":
        set_active_device(device_id)

    flash("Equipamento atualizado com sucesso.", "success")
    return redirect(url_for("configuracoes"))


@app.route("/equipamentos/<int:device_id>/ativar", methods=["POST"])
def ativar_equipamento(device_id):
    if not get_device(device_id):
        flash("Equipamento nao encontrado.", "error")
        return redirect(url_for("configuracoes"))

    set_active_device(device_id)
    flash("Equipamento ativo alterado.", "success")
    return redirect(url_for("configuracoes"))


@app.route("/equipamentos/<int:device_id>/excluir", methods=["POST"])
def excluir_equipamento(device_id):
    device = get_device(device_id)
    if not device:
        flash("Equipamento nao encontrado.", "error")
        return redirect(url_for("configuracoes"))

    with get_db() as conn:
        conn.execute("DELETE FROM devices WHERE id = ?", (device_id,))
        next_device = conn.execute(
            "SELECT id FROM devices ORDER BY id LIMIT 1"
        ).fetchone()
        conn.commit()

    if device["is_active"] and next_device:
        set_active_device(next_device["id"])

    flash("Equipamento excluido.", "success")
    return redirect(url_for("configuracoes"))


@app.errorhandler(404)
def page_not_found(error):
    active_device = get_active_device()
    return render_template("erro.html", device=active_device, error_detail="Pagina nao encontrada."), 404


@app.errorhandler(500)
def internal_error(error):
    active_device = get_active_device()
    return render_template("erro.html", device=active_device, error_detail="Erro interno do servidor."), 500


setup_app()


if __name__ == "__main__":
    app.run(port=FLASK_PORT, host=FLASK_HOST, debug=FLASK_DEBUG, threaded=True)

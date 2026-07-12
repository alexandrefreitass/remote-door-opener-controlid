import json
import os
import signal
import socket
import subprocess
import sys
import threading
import time
import urllib.error
import urllib.request
import webbrowser
from pathlib import Path
from tkinter import BOTH, DISABLED, NORMAL, Button, Frame, Label, Tk, messagebox


APP_TITLE = "Controle de Acesso"


def find_project_dir():
    if getattr(sys, "frozen", False):
        exe_dir = Path(sys.executable).resolve().parent
        candidates = [exe_dir, exe_dir.parent]
    else:
        candidates = [Path(__file__).resolve().parent]

    for candidate in candidates:
        if (candidate / "run_prod.py").exists():
            return candidate

    return candidates[0]


PROJECT_DIR = find_project_dir()
CONFIG_PATH = PROJECT_DIR / "config.env"
RUN_PROD_PATH = PROJECT_DIR / "run_prod.py"
LOG_DIR = PROJECT_DIR / "logs"
PID_PATH = PROJECT_DIR / "server.pid"


def read_config():
    config = {
        "FLASK_HOST": "0.0.0.0",
        "FLASK_PORT": "5000",
    }

    if not CONFIG_PATH.exists():
        return config

    for line in CONFIG_PATH.read_text(encoding="utf-8", errors="ignore").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        config[key.strip()] = value.strip()

    return config


def get_python_executable():
    pythonw = PROJECT_DIR / "venv" / "Scripts" / "pythonw.exe"
    python = PROJECT_DIR / "venv" / "Scripts" / "python.exe"

    if pythonw.exists():
        return str(pythonw)
    if python.exists():
        return str(python)
    return sys.executable if not getattr(sys, "frozen", False) else "python"


def is_port_open(port):
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.settimeout(0.25)
        return sock.connect_ex(("127.0.0.1", port)) == 0


def read_server_identity():
    try:
        identity = json.loads(PID_PATH.read_text(encoding="utf-8"))
        pid = int(identity["pid"])
        instance_token = str(identity["instance_token"])
    except (OSError, ValueError, KeyError, TypeError, json.JSONDecodeError):
        return None

    return {"pid": pid, "instance_token": instance_token}


def server_identity_matches(url, identity):
    if not identity:
        return False

    try:
        with urllib.request.urlopen(f"{url}/health", timeout=0.5) as response:
            payload = json.loads(response.read().decode("utf-8"))
    except (OSError, ValueError, urllib.error.URLError, json.JSONDecodeError):
        return False

    return (
        payload.get("application") == "controle-de-acesso-controlid"
        and payload.get("instance_token") == identity["instance_token"]
    )


def terminate_server(identity):
    if not identity:
        return False

    try:
        os.kill(identity["pid"], signal.SIGTERM)
    except (OSError, ProcessLookupError):
        return False

    try:
        PID_PATH.unlink(missing_ok=True)
    except OSError:
        pass

    return True


class LauncherApp:
    def __init__(self, root):
        self.root = root
        self.root.title(APP_TITLE)
        self.root.geometry("420x260")
        self.root.minsize(420, 260)
        self.root.protocol("WM_DELETE_WINDOW", self.on_close)

        self.config = read_config()
        self.port = int(self.config.get("FLASK_PORT", "5000"))
        self.url = f"http://localhost:{self.port}"
        self.process = None
        self.external_identity = None
        self.log_file = None

        self.build_ui()
        self.refresh_status()

    def build_ui(self):
        container = Frame(self.root, padx=22, pady=20)
        container.pack(fill=BOTH, expand=True)

        Label(container, text=APP_TITLE, font=("Segoe UI", 18, "bold")).pack(anchor="w")
        Label(
            container,
            text="Servidor interno de abertura remota",
            font=("Segoe UI", 10),
        ).pack(anchor="w", pady=(2, 16))

        self.status_label = Label(
            container,
            text="Status: verificando...",
            font=("Segoe UI", 11, "bold"),
        )
        self.status_label.pack(anchor="w", pady=(0, 8))

        self.url_label = Label(container, text=self.url, font=("Segoe UI", 10))
        self.url_label.pack(anchor="w", pady=(0, 18))

        actions = Frame(container)
        actions.pack(fill="x")

        self.start_button = Button(actions, text="Iniciar sistema", command=self.start_server)
        self.start_button.pack(side="left", fill="x", expand=True, padx=(0, 6))

        self.stop_button = Button(actions, text="Parar", command=self.stop_server)
        self.stop_button.pack(side="left", fill="x", expand=True, padx=6)

        self.browser_button = Button(actions, text="Abrir navegador", command=self.open_browser)
        self.browser_button.pack(side="left", fill="x", expand=True, padx=(6, 0))

        Label(
            container,
            text="Mantenha esta janela aberta enquanto o sistema estiver em uso.",
            font=("Segoe UI", 9),
        ).pack(anchor="w", pady=(18, 0))

    def set_status(self, text):
        self.status_label.config(text=f"Status: {text}")

    def refresh_status(self):
        if self.process and self.process.poll() is None:
            self.set_running_status()
        elif self.process:
            self.process = None
            if self.log_file:
                self.log_file.close()
                self.log_file = None
            self.set_stopped_status()
        else:
            identity = read_server_identity()
            if is_port_open(self.port) and server_identity_matches(self.url, identity):
                self.external_identity = identity
                self.set_running_status()
            elif is_port_open(self.port):
                self.external_identity = None
                self.set_external_port_status()
            else:
                self.external_identity = None
                self.set_stopped_status()

        self.root.after(1500, self.refresh_status)

    def set_stopped_status(self):
        self.set_status("parado")
        self.start_button.config(state=NORMAL)
        self.stop_button.config(state=DISABLED)
        self.browser_button.config(state=DISABLED)

    def set_external_port_status(self):
        self.set_status("porta em uso por outro processo")
        self.start_button.config(state=DISABLED)
        self.stop_button.config(state=DISABLED)
        self.browser_button.config(state=NORMAL)

    def set_running_status(self):
        self.set_status("rodando")
        self.start_button.config(state=DISABLED)
        self.stop_button.config(state=NORMAL)
        self.browser_button.config(state=NORMAL)

    def start_server(self):
        if not RUN_PROD_PATH.exists():
            messagebox.showerror(
                APP_TITLE,
                f"Nao encontrei o arquivo run_prod.py em:\n{PROJECT_DIR}",
            )
            return

        if is_port_open(self.port):
            messagebox.showinfo(APP_TITLE, "O sistema ja parece estar rodando nessa porta.")
            self.open_browser()
            return

        LOG_DIR.mkdir(exist_ok=True)
        self.log_file = (LOG_DIR / "server.log").open("a", encoding="utf-8")

        env = os.environ.copy()
        env["PYTHONIOENCODING"] = "utf-8"

        creationflags = 0
        if os.name == "nt":
            creationflags = subprocess.CREATE_NO_WINDOW

        try:
            self.process = subprocess.Popen(
                [get_python_executable(), str(RUN_PROD_PATH)],
                cwd=str(PROJECT_DIR),
                stdout=self.log_file,
                stderr=subprocess.STDOUT,
                env=env,
                creationflags=creationflags,
            )
        except OSError as exc:
            messagebox.showerror(APP_TITLE, f"Nao foi possivel iniciar o sistema:\n{exc}")
            return

        threading.Thread(target=self.open_when_ready, daemon=True).start()
        self.refresh_status()

    def open_when_ready(self):
        for _ in range(30):
            if is_port_open(self.port):
                webbrowser.open(self.url)
                return
            time.sleep(0.3)

    def stop_server(self):
        if self.process and self.process.poll() is None:
            self.process.terminate()
            try:
                self.process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                self.process.kill()
        elif self.external_identity and server_identity_matches(
            self.url, self.external_identity
        ):
            terminate_server(self.external_identity)
            time.sleep(0.5)
        else:
            self.process = None
            self.refresh_status()
            return

        self.process = None
        self.external_identity = None
        if self.log_file:
            self.log_file.close()
            self.log_file = None
        self.refresh_status()

    def open_browser(self):
        webbrowser.open(self.url)

    def on_close(self):
        if (self.process and self.process.poll() is None) or (
            self.external_identity
            and server_identity_matches(self.url, self.external_identity)
        ):
            should_stop = messagebox.askyesno(
                APP_TITLE,
                "Deseja parar o sistema antes de fechar?",
            )
            if should_stop:
                self.stop_server()

        self.root.destroy()


def main():
    root = Tk()
    LauncherApp(root)
    root.mainloop()


if __name__ == "__main__":
    main()

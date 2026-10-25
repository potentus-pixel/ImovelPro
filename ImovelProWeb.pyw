"""Inicializa a versão web sem console e abre o navegador padrão."""

import threading
import webbrowser
import os

import web_app


if __name__ == "__main__":
    configured_host = os.getenv("IMOVELPRO_WEB_HOST", "127.0.0.1")
    host = "127.0.0.1" if configured_host == "0.0.0.0" else configured_host
    port = int(os.getenv("IMOVELPRO_WEB_PORT", "8000"))
    threading.Timer(
        1.2, lambda: webbrowser.open(f"http://{host}:{port}")).start()
    web_app.run()

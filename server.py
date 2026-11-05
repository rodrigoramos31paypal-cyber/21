"""Entrada do servidor local 21 Dias de Foco."""
import os
from server_v4 import app

if __name__ == "__main__":
    app.run(host="127.0.0.1", port=int(os.environ.get("PORT", "8080")), debug=False)

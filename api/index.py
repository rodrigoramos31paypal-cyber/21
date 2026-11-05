"""Única entrada Vercel: todos os pedidos passam pelas permissões Flask."""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from server_v4 import app

"""Entry point for Streamlit Cloud."""
import os
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
# Always set a valid cross-platform DB path unless already correctly set
_default_db = str(Path(tempfile.gettempdir()) / "kpis.db")
_current = os.environ.get("DUCKDB_PATH", "")
# Override if unset or if it looks like a raw Unix path on Windows
if not _current or (_current.startswith("/") and os.name == "nt"):
    os.environ["DUCKDB_PATH"] = _default_db

import streamlit as st
from app.seed import seed_database
from app.dashboard import render

seed_database()
render()

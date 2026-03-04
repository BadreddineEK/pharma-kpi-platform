"""Entry point for Streamlit Cloud."""
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
os.environ.setdefault("DUCKDB_PATH", "/tmp/kpis.db")

import streamlit as st
from app.seed import seed_database
from app.dashboard import render

seed_database()
render()

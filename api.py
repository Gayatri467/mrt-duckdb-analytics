import os
from flask import Flask, send_from_directory

app = Flask(__name__)

# Root directory path
BASE_DIR = os.path.abspath(os.path.dirname(__file__))

@app.route("/")
def home():
    """Serves the main frontend page."""
    return send_from_directory(BASE_DIR, "index.html")

@app.route("/<path:filename>")
def serve_static(filename):
    """
    Serves static assets (JS, CSS) and nested data files 
    (e.g., /output/task2/final_unique.parquet).
    Werkzeug/Flask handles HTTP Range Requests automatically for DuckDB-WASM.
    """
    return send_from_directory(BASE_DIR, filename)

if __name__ == "__main__":
    # Standard local Flask runner
    app.run(debug=True, host="0.0.0.0", port=5000)
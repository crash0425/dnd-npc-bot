from flask import Flask
import logging
from npc_bot_worker import run_worker  # This must match the worker file name (no `.py`)

app = Flask(__name__)

@app.route("/")
def home():
    return "✅ NPC Bot Web Service is up and running."

@app.route("/test-worker")
def test_worker():
    try:
        run_worker()
        return "✅ Worker completed successfully."
    except Exception as e:
        logging.exception("Worker failed:")
        return f"❌ Worker failed: {str(e)}", 500

if __name__ == "__main__":
    app.run(debug=True)

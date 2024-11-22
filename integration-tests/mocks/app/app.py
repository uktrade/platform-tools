from flask import Flask
from flask import jsonify

app = Flask(__name__)


@app.route("/status", methods=["GET"])
def status():
    return jsonify({"status": "ok"})


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)

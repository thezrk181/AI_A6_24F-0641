from __future__ import annotations

from flask import Flask, jsonify, render_template, request

from engine import AgentEpisode

app = Flask(__name__)

CURRENT_EPISODE: AgentEpisode | None = None


def _get_episode() -> AgentEpisode:
    global CURRENT_EPISODE
    if CURRENT_EPISODE is None:
        CURRENT_EPISODE = AgentEpisode(rows=4, cols=4, pit_probability=0.2)
    return CURRENT_EPISODE


@app.route("/")
def index():
    return render_template("index.html")


@app.post("/api/new-episode")
def new_episode():
    global CURRENT_EPISODE
    data = request.get_json(silent=True) or {}

    rows = int(data.get("rows", 4))
    cols = int(data.get("cols", 4))
    pit_probability = float(data.get("pitProbability", 0.2))

    rows = max(2, min(rows, 10))
    cols = max(2, min(cols, 10))
    pit_probability = max(0.05, min(pit_probability, 0.45))

    CURRENT_EPISODE = AgentEpisode(rows=rows, cols=cols, pit_probability=pit_probability)
    return jsonify(CURRENT_EPISODE.export_state())


@app.get("/api/state")
def get_state():
    return jsonify(_get_episode().export_state())


@app.post("/api/auto-step")
def auto_step():
    episode = _get_episode()
    episode.auto_step()
    return jsonify(episode.export_state())


@app.post("/api/move")
def move():
    episode = _get_episode()
    data = request.get_json(silent=True) or {}
    r = int(data.get("r", -1))
    c = int(data.get("c", -1))

    if not (0 <= r < episode.rows and 0 <= c < episode.cols):
        return jsonify({"error": "Target is out of grid bounds."}), 400

    episode.move_if_safe((r, c))
    return jsonify(episode.export_state())


if __name__ == "__main__":
    app.run(debug=True)

from flask import Flask, render_template, jsonify, request
import requests
import re

app = Flask(__name__, template_folder="../templates", static_folder="../static")


# Validate draft ID to ensure it's numeric
def validate_draft_id(draft_id):
    draft_id = draft_id.strip()
    return draft_id if re.match(r"^\d+$", draft_id) else None


# Fetch all draft picks using draft ID
def fetch_draft_picks(draft_id):
    draft_id = validate_draft_id(draft_id)
    if not draft_id:
        return None, "Invalid draft ID. Please enter a valid numeric draft ID."

    url = f"https://api.sleeper.app/v1/draft/{draft_id}/picks"
    response = requests.get(url)

    if response.status_code == 200:
        return response.json(), None
    return None, "Failed to fetch draft picks from Sleeper API."


# Fetch manager usernames using Sleeper User ID
def fetch_username(user_id):
    url = f"https://api.sleeper.app/v1/user/{user_id}"
    response = requests.get(url)

    if response.status_code == 200:
        user_data = response.json()
        return user_data.get("username", "Unknown Username")

    return "Unknown Username"


# Extract kicker draft order and assign draft pick placeholders
def get_kicker_draft_order(draft_picks):
    if not draft_picks:
        return [], "No draft picks found!"

    kicker_picks = []
    manager_cache = {}  # Cache usernames to reduce redundant API calls
    draft_slots = set()  # Track unique draft slots to determine league size

    for pick in draft_picks:
        metadata = pick.get("metadata", {})
        position = metadata.get("position", "").strip().upper()  # Normalize position
        user_id = pick.get("picked_by", "")

        if user_id and user_id not in manager_cache:
            manager_cache[user_id] = fetch_username(user_id)

        if position == "K":
            draft_slots.add(pick["draft_slot"])  # Track unique draft slots

            kicker_picks.append(
                {
                    "pick_number": pick["pick_no"],
                    "round": pick["round"],
                    "draft_slot": pick["draft_slot"],
                    "username": manager_cache.get(user_id, "Unknown Manager"),
                    "user_id": user_id,
                    "player_name": f"{metadata.get('first_name', '')} {metadata.get('last_name', '')}".strip(),
                }
            )

    if not kicker_picks:
        return [], "No kickers found in the draft picks!"

    # Sort by round and pick number
    kicker_picks.sort(key=lambda x: (x["round"], x["pick_number"]))

    # Determine league size (highest draft_slot number)
    league_size = (
        max(draft_slots) if draft_slots else len(kicker_picks)
    )  # Fallback if draft slots are missing

    # Assign 1.01, 1.02, ..., 1.N → 2.01, 2.02 placeholders
    for idx, pick in enumerate(kicker_picks):
        round_number = (idx // league_size) + 1
        pick_number = (idx % league_size) + 1
        pick["rookie_pick"] = f"{round_number}.{pick_number:02d}"

    return kicker_picks, None


@app.route("/")
def index():
    return render_template("index.html")


@app.route("/kicker_order", methods=["GET"])
def kicker_order():
    draft_id = request.args.get("draft_id", "").strip()
    draft_picks, error = fetch_draft_picks(draft_id)

    if error:
        return jsonify({"error": error}), 400

    kicker_order, error = get_kicker_draft_order(draft_picks)

    if error:
        return jsonify({"error": error}), 404

    return jsonify(kicker_order)


if __name__ == "__main__":
    app.run(debug=True)

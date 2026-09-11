from flask import Flask, render_template, request, redirect, url_for, session
from datetime import datetime
import sqlite3

app = Flask(__name__)
app.secret_key = "lillah-foundation-demo-key"

# ACCESS CODES
VOTER_CODE = "LillahFoundation2024"
LEADER_CODE = "LillahLeader2024"

# TEMPORARY TESTING TIME
# We will change this back to the real election time later.
VOTING_START = datetime(2026, 9, 12, 12, 0)
VOTING_END = datetime(2026, 9, 13, 12, 0)

# CANDIDATES
candidates = [
    "Arsalan Mahmood",
    "Taslim Akhtar",
    "Saleheen Salam",
    "Sikandar Azam",
    "Lareb Khan"
]

DATABASE = "votes.db"


def get_db():
    connection = sqlite3.connect(DATABASE)
    connection.row_factory = sqlite3.Row
    return connection


def create_database():
    connection = get_db()

    connection.execute("""
        CREATE TABLE IF NOT EXISTS votes (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            voter_name TEXT NOT NULL,
            candidate TEXT NOT NULL
        )
    """)

    connection.commit()
    connection.close()


def voting_is_open():
    now = datetime.now()
    return VOTING_START <= now < VOTING_END


@app.route("/")
def home():
    return render_template("index.html")


@app.route("/login", methods=["POST"])
def login():
    code = request.form.get("code")

    if code == LEADER_CODE:
        session["leader"] = True
        return redirect(url_for("leader"))

    if code == VOTER_CODE:
        if not voting_is_open():
            return """
            <h1>Voting is closed</h1>
            <p>The voting period has ended.</p>
            """

        session["voter_access"] = True
        return redirect(url_for("vote"))

    return """
    <h1>Invalid Access Code</h1>
    <p>Please enter the correct access code.</p>
    <a href="/">Go back</a>
    """


@app.route("/vote")
def vote():
    if not session.get("voter_access"):
        return redirect(url_for("home"))

    if not voting_is_open():
        return """
        <h1>Voting is closed</h1>
        <p>The voting period has ended.</p>
        """

    return render_template("vote.html", candidates=candidates)


@app.route("/submit_vote", methods=["POST"])
def submit_vote():
    if not session.get("voter_access"):
        return redirect(url_for("home"))

    if not voting_is_open():
        return """
        <h1>Voting is closed</h1>
        <p>Your vote could not be submitted.</p>
        """

    voter_name = request.form.get("voter_name", "").strip()
    candidate = request.form.get("candidate", "").strip()

    if not voter_name:
        return "<h1>Please enter your name.</h1>"

    if candidate not in candidates:
        return "<h1>Invalid candidate.</h1>"

    if session.get("has_voted"):
        return """
        <h1>You have already voted.</h1>
        <p>Your vote cannot be changed.</p>
        """

    connection = get_db()

    connection.execute(
        "INSERT INTO votes (voter_name, candidate) VALUES (?, ?)",
        (voter_name, candidate)
    )

    connection.commit()
    connection.close()

    session["has_voted"] = True

    return render_template(
        "success.html",
        voter_name=voter_name,
        candidate=candidate
    )


@app.route("/results")
def results():
    connection = get_db()

    vote_counts = {}

    for candidate in candidates:
        vote_counts[candidate] = 0

    rows = connection.execute(
        "SELECT candidate, COUNT(*) AS total FROM votes GROUP BY candidate"
    ).fetchall()

    connection.close()

    for row in rows:
        vote_counts[row["candidate"]] = row["total"]

    highest_votes = max(vote_counts.values()) if vote_counts else 0

    winners = [
        candidate
        for candidate, count in vote_counts.items()
        if count == highest_votes and highest_votes > 0
    ]

    return render_template(
        "results.html",
        vote_counts=vote_counts,
        winners=winners,
        highest_votes=highest_votes
    )


@app.route("/leader")
def leader():
    if not session.get("leader"):
        return redirect(url_for("home"))

    connection = get_db()

    votes = connection.execute(
        "SELECT voter_name, candidate FROM votes ORDER BY id ASC"
    ).fetchall()

    vote_counts = {}

    for candidate in candidates:
        vote_counts[candidate] = 0

    for vote in votes:
        vote_counts[vote["candidate"]] += 1

    connection.close()

    return render_template(
        "leader.html",
        votes=votes,
        vote_counts=vote_counts
    )


if __name__ == "__main__":
    create_database()
    app.run(debug=True)
from flask import Flask, render_template, request, redirect, url_for, session
from datetime import datetime
from zoneinfo import ZoneInfo
import sqlite3
import os

app = Flask(__name__)

app.secret_key = os.environ.get(
    "SECRET_KEY",
    "lillah-foundation-demo-key"
)

# ACCESS CODES
VOTER_CODE = "LillahFoundation2024"
LEADER_CODE = "LillahLeader2024"

# TEMPORARY TESTING TIME
# Voting is temporarily open so we can check the voting page.
# We will change this back to the real election time after testing.

VOTING_START = datetime(
    2026, 9, 12, 0, 0,
    tzinfo=ZoneInfo("Asia/Kolkata")
)

VOTING_END = datetime(
    2026, 9, 13, 23, 59,
    tzinfo=ZoneInfo("Asia/Kolkata")
)

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
    now = datetime.now(ZoneInfo("Asia/Kolkata"))
    return VOTING_START <= now < VOTING_END


@app.route("/")
def home():
    return render_template("index.html")


@app.route("/login", methods=["POST"])
def login():

    code = request.form.get("code", "").strip()

    if code == LEADER_CODE:
        session.clear()
        session["leader"] = True
        return redirect(url_for("leader"))

    if code == VOTER_CODE:

        if not voting_is_open():
            return """
            <h1>Voting is closed</h1>
            <p>The voting period is currently closed.</p>
            <a href="/">Go back</a>
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

    if session.get("has_voted"):
        return """
        <h1>You have already voted.</h1>
        <p>Your vote cannot be changed or submitted again.</p>
        <a href="/">Return to Home</a>
        """

    if not voting_is_open():
        return """
        <h1>Voting is closed</h1>
        <p>The voting period has ended.</p>
        <a href="/">Return to Home</a>
        """

    return render_template(
        "vote.html",
        candidates=candidates
    )


@app.route("/submit_vote", methods=["POST"])
def submit_vote():

    if not session.get("voter_access"):
        return redirect(url_for("home"))

    if session.get("has_voted"):
        return """
        <h1>You have already voted.</h1>
        <p>Your vote cannot be changed.</p>
        """

    if not voting_is_open():
        return """
        <h1>Voting is closed</h1>
        <p>Your vote could not be submitted.</p>
        """

    voter_name = request.form.get(
        "voter_name",
        ""
    ).strip()

    candidate = request.form.get(
        "candidate",
        ""
    ).strip()

    if not voter_name:
        return """
        <h1>Please enter your name.</h1>
        <a href="/vote">Go back</a>
        """

    if candidate not in candidates:
        return """
        <h1>Invalid candidate.</h1>
        <a href="/vote">Go back</a>
        """

    connection = get_db()

    connection.execute(
        """
        INSERT INTO votes
        (voter_name, candidate)
        VALUES (?, ?)
        """,
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
        """
        SELECT candidate, COUNT(*) AS total
        FROM votes
        GROUP BY candidate
        """
    ).fetchall()

    connection.close()

    for row in rows:
        vote_counts[row["candidate"]] = row["total"]

    highest_votes = max(vote_counts.values())

    winners = [
        candidate
        for candidate, count in vote_counts.items()
        if count == highest_votes and highest_votes > 0
    ]

    return render_template(
        "results.html",
        vote_counts=vote_counts,
        winners=winners,
        highest_votes=highest_votes,
        voting_open=voting_is_open()
    )


@app.route("/leader")
def leader():

    if not session.get("leader"):
        return redirect(url_for("home"))

    connection = get_db()

    votes = connection.execute(
        """
        SELECT voter_name, candidate
        FROM votes
        ORDER BY id ASC
        """
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


# Create database when the application starts
create_database()


if __name__ == "__main__":
    app.run(
        host="0.0.0.0",
        port=int(os.environ.get("PORT", 5000)),
        debug=False
    )

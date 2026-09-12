from flask import Flask, render_template, request, redirect, url_for, session
from datetime import datetime
from zoneinfo import ZoneInfo
import os
import psycopg
from psycopg.rows import dict_row
app = Flask(__name__)
app.secret_key = os.environ.get(
    "SECRET_KEY",
    "lillah-foundation-demo-key"
)
# ACCESS CODES
VOTER_CODE = "LillahFoundation2024"
LEADER_CODE = "LillahLeader2024"
# VOTING TIME
# Voting is now CLOSED.
VOTING_START = datetime(
    2026, 9, 12, 15, 0,
    tzinfo=ZoneInfo("Asia/Kolkata")
)
VOTING_END = datetime(
    2026, 9, 12, 20, 0,
    tzinfo=ZoneInfo("Asia/Kolkata")
)
# ELECTION ROUND
ELECTION_ID = "2026-09-12-NEW"
# CANDIDATES
candidates = [
    "Arsalan Mahmood",
    "Taslim Akhtar",
    "Saleheen Salam",
    "Sikandar Azam",
    "Lareb Khan"
]
# POSTGRES DATABASE
DATABASE_URL = os.environ.get("DATABASE_URL")
def get_db():
    connection = psycopg.connect(
        DATABASE_URL,
        row_factory=dict_row
    )
    return connection
def create_database():
    connection = get_db()
    connection.execute("""
        CREATE TABLE IF NOT EXISTS votes (
            id SERIAL PRIMARY KEY,
            voter_name TEXT NOT NULL,
            candidate TEXT NOT NULL
        )
    """)
    connection.execute("""
        CREATE TABLE IF NOT EXISTS restored_votes (
            id INTEGER PRIMARY KEY
        )
    """)
    connection.commit()
    connection.close()
# RESTORE THE 10 OLD VOTES
# This does NOT delete or modify existing votes.
# It adds these 10 only once.
def restore_old_votes():
    connection = get_db()
    already_restored = connection.execute(
        "SELECT id FROM restored_votes WHERE id = 1"
    ).fetchone()
    if not already_restored:
        old_votes = [
            ("Soyeb", "Lareb Khan"),
            ("Arsalan Mahmood", "Sikandar Azam"),
            ("Taslimakhtar", "Taslim Akhtar"),
            ("Md Saleheen Shaikh", "Saleheen Salam"),
            ("Lareb Khan", "Sikandar Azam"),
            ("Md Zawed", "Sikandar Azam"),
            ("Md. Zeeshan Hasan", "Sikandar Azam"),
            ("Zaid Farooque", "Sikandar Azam"),
            ("Md Arif Hussain", "Lareb Khan"),
            ("Farhan Khan", "Saleheen Salam")
        ]
        cursor = connection.cursor()
        cursor.executemany(
            """
            INSERT INTO votes
            (voter_name, candidate)
            VALUES (%s, %s)
            """,
            old_votes
        )
        connection.execute(
            "INSERT INTO restored_votes (id) VALUES (1)"
        )
        connection.commit()
        cursor.close()
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
    # LEADER ACCESS ALWAYS WORKS
    if code == LEADER_CODE:
        session.clear()
        session["leader"] = True
        return redirect(url_for("leader"))
    # VOTER ACCESS IS NOW CLOSED
    if code == VOTER_CODE:
        return """
        <h1>Voting is Closed</h1>
        <p>
            The voting period has ended.
        </p>
        <p>
            Thank you to everyone who participated.
        </p>
        <p>
            <a href="/results">View Final Results</a>
        </p>
        <p>
            <a href="/">Go back</a>
        </p>
        """
    return """
    <h1>Invalid Access Code</h1>
    <p>Please enter the correct access code.</p>
    <a href="/">Go back</a>
    """
@app.route("/vote")
def vote():
    return """
    <h1>Voting is Closed</h1>
    <p>The voting period has ended.</p>
    <p>No more votes can be submitted.</p>
    <p>
        <a href="/results">View Final Results</a>
    </p>
    <p>
        <a href="/">Return to Home</a>
    </p>
    """
@app.route("/submit_vote", methods=["POST"])
def submit_vote():
    return """
    <h1>Voting is Closed</h1>
    <p>The voting period has ended.</p>
    <p>Your vote could not be submitted.</p>
    <p>
        <a href="/results">View Final Results</a>
    </p>
    """
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
        voting_open=False
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
# CREATE DATABASE FIRST
create_database()
# THEN RESTORE THE 10 OLD VOTES
restore_old_votes()
if __name__ == "__main__":
    app.run(
        host="0.0.0.0",
        port=int(os.environ.get("PORT", 5000)),
        debug=False
    )

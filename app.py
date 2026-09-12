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
VOTING_START = datetime(
    2026, 9, 12, 15, 0,
    tzinfo=ZoneInfo("Asia/Kolkata")
)

VOTING_END = datetime(
    2026, 9, 13, 15, 0,
    tzinfo=ZoneInfo("Asia/Kolkata")
)

# NEW ELECTION ROUND
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
# This does NOT delete existing votes.
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

    if code == LEADER_CODE:
        session.clear()
        session["leader"] = True
        return redirect(url_for("leader"))

    if code == VOTER_CODE:

        if not voting_is_open():
            return """
            <h1>Voting is closed</h1>
            <p>
                Voting is open from 12 September 2026 at 3:00 PM
                to 13 September 2026 at 3:00 PM IST.
            </p>
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

    if session.get("voted_election") == ELECTION_ID:
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

    if session.get("voted_election") == ELECTION_ID:
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
        VALUES (%s, %s)
        """,
        (voter_name, candidate)
    )

    connection.commit()
    connection.close()

    session["voted_election"] = ELECTION_ID

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

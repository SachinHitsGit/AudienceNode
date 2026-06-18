import socket
import os 
import sqlite3
import threading
import time
import json
from datetime import datetime

# pyrefly: ignore [missing-import]
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from dotenv import load_dotenv

from twh_comm import run_analysis_pipeline

load_dotenv()

TWITCH_SERVER   = "irc.chat.twitch.tv"
PORT            = 6667
TOKEN           = os.getenv("TWITCH_TOKEN")
USERNAME        = os.getenv("TWITCH_USERNAME")
CHANNEL         = f"#{USERNAME}"
DB_PATH         = os.getenv("DB_PATH")

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"]
)

STATE = {
    "is_listening": False,
    "active_poll_id": None,
    "message_buffer": [],
    "last_result": None,
    "irc_thread": None,
    "writer_thread": None,
}

def init_db():
    conn = sqlite3.connect(DB_PATH, check_same_thread=False)
    cursor = conn.cursor()

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS chat_logs(
        id          INTEGER PRIMARY KEY AUTOINCREMENT,
        timestamp   TEXT,
        username    TEXT,
        message     TEXT
        )
    """)

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS polls(
        id                  INTEGER PRIMARY KEY AUTOINCREMENT,
        start_time          TEXT,
        stop_time           TEXT,
        sponsor_keywords    TEXT
        )
    """)

    conn.commit()
    conn.close()

init_db()

def batch_writer():
    while STATE["is_listening"]:
        time.sleep(5)
        if STATE["message_buffer"]:
            conn =  sqlite3.connect(DB_PATH, check_same_thread=False)
            cursor = conn.cursor()
            cursor.executemany(
                "INSERT INTO chat_logs (timestamp, username, message) VALUES (?,?,?)",
                STATE["message_buffer"].copy()
            )
            conn.commit()
            conn.close()
            STATE["message_buffer"].clear()
            print(f"Flushed buffer to DB")

def irc_listener():
    irc_socket = socket.socket()
    irc_socket.connect((TWITCH_SERVER,PORT))
    irc_socket.send(f"PASS {TOKEN}\r\n".encode("utf-8"))
    irc_socket.send(f"NICK {USERNAME}\r\n".encode("utf-8"))
    irc_socket.send(f"JOIN {CHANNEL}\r\n".encode("utf-8"))
    irc_socket.settimeout(1.0)

    print(f"IRC connected. Listening to {CHANNEL}")

    while STATE["is_listening"]:
        try:
            raw_data = irc_socket.recv(2048).decode("utf-8")
            if not raw_data:
                break

            lines = raw_data.split("\r\n")

            for line in lines:
                if not line:
                    continue
                print(f"Raw from Twitch: {line}")
                if line.startswith("PING"):
                    irc_socket.send("PONG :tmi.twitch.tv\r\n".encode("utf-8"))
                    print("Keep alive. PING-PONG handled.")

                elif "PRIVMSG" in raw_data:
                    try:
                        username     = line.split("!")[0][1:]
                        message      = line.split("PRIVMSG")[1].split(" :", 1)[1].strip()
                        current_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                        STATE["message_buffer"].append((current_time, username, message))
                        print(f"[{username}]: {message}")
                    except IndexError:
                        continue
        except socket.timeout:
            continue
    irc_socket.close()
    print("IRC socket closed.")

@app.post("/poll/start")
def poll_start():
    global STATE

    if STATE["is_listening"]:
        return {"error": "A poll is already running."}

    start_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    conn = sqlite3.connect(DB_PATH, check_same_thread=False)
    curs = conn.cursor()
    curs.execute(
        "INSERT INTO polls (start_time) values (?)",
        (start_time,)
    )
    conn.commit()
    poll_id = curs.lastrowid
    conn.close()

    STATE["is_listening"]   = True
    STATE["active_poll_id"] = poll_id
    STATE["message_buffer"] = []

    STATE["irc_thread"] = threading.Thread(target=irc_listener, daemon=True)
    STATE["writer_thread"] = threading.Thread(target=batch_writer, daemon=True)

    STATE["irc_thread"].start()
    STATE["writer_thread"].start()

    return {
        "status": "started",
        "poll_id": poll_id,
        "start_time": start_time,
    }

@app.post("/poll/stop")
def poll_stop():
    global STATE

    if not STATE["is_listening"]:
        return {"error": "No poll is currently running."}

    STATE["is_listening"]= False
    
    if STATE["irc_thread"]:
        STATE["irc_thread"].join()
    if STATE["writer_thread"]:
        STATE["writer_thread"].join()

    stop_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    if STATE["message_buffer"]:
        conn = sqlite3.connect(DB_PATH, check_same_thread=False)
        curs = conn.cursor()
        curs.executemany(
            "INSERT INTO chat_logs (timestamp, username, message) VALUES (?, ?, ?)",
            STATE["message_buffer"].copy()
        )
        conn.commit()
        conn.close()
        STATE["message_buffer"].clear()
    conn = sqlite3.connect(DB_PATH, check_same_thread=False)
    curs = conn.cursor()
    curs.execute(
        "UPDATE polls SET stop_time = ? WHERE id = ?",
        (stop_time,STATE["active_poll_id"])
    )

    curs.execute(
        "SELECT start_time FROM polls WHERE id = ?",
        (STATE["active_poll_id"],)
    )

    row = curs.fetchone()
    start_time = row[0]
    conn.commit()
    conn.close()

    print(f"Poll stopped. Running community clustering for {start_time} -> {stop_time}")

    result = run_analysis_pipeline(start_time, stop_time)

    final_result = {
        "poll_id"   : STATE["active_poll_id"],
        "start_time": start_time,
        "stop_time" : stop_time,
        "clusters"  : result.get("clusters"),
        "error"     : result.get("error")
    }

    STATE["last_result"] = final_result
    STATE["active_poll_id"] = None

    with open("poll_result.json", "w") as f:
        json.dump(final_result, f, indent=2)
    return final_result

@app.get("/result")
def get_result():
    if STATE["last_result"] is None:
        return {"error": "No results yet. Run a poll first."}
    return STATE["last_result"]

@app.get("/status")
def get_status():
    return {
        "is_listening"  : STATE["is_listening"],
        "active_poll_id": STATE["active_poll_id"],
        "buffer_size"   : len(STATE["message_buffer"]),
        "buffer_message": STATE["message_buffer"],
    }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
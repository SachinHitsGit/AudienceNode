import socket
import sys
import os 
import sqlite3
from dotenv import load_dotenv
from datetime import datetime

load_dotenv()

# 1. Setup Configuration
TWITCH_SERVER = "irc.chat.twitch.tv"
PORT = 6667
TOKEN = os.getenv("TWITCH_TOKEN")
USERNAME = os.getenv("TWITCH_USERNAME")
CHANNEL = f"#{USERNAME}"

# 3. DB initialization
db_connection = sqlite3.connect("twitch_chat.db")
db_cursor = db_connection.cursor()

db_cursor.execute("""
CREATE TABLE IF NOT EXISTS chat_logs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    timestamp TEXT,
    username TEXT,
    message TEXT
    )
""")
db_connection.commit()

# 3.a Network Connect
irc_socket = socket.socket()
irc_socket.connect((TWITCH_SERVER, PORT))

# 3.b Authentication Handshake
irc_socket.send(f"PASS {TOKEN}\r\n".encode('utf-8'))
irc_socket.send(f"NICK {USERNAME}\r\n".encode('utf-8'))
irc_socket.send(f"JOIN {CHANNEL}\r\n".encode('utf-8'))

print(f"📡 Connected. Listening to {CHANNEL}...")

# 4. Continuous Ingestion Loop
try:
    while True:
        raw_data = irc_socket.recv(2048).decode('utf-8')
        print(f"DEBUG: {raw_data}")
        if not raw_data:
            break

        # Keepalive Handshake
        if raw_data.startswith("PING"):
            irc_socket.send("PONG :tmi.twitch.tv\r\n".encode('utf-8'))
            
        elif "PRIVMSG" in raw_data:
            try:
                username = raw_data.split("!")[0][1:]
                message = raw_data.split("PRIVMSG")[1].split(" :", 1)[1].strip()
                current_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                
                # 5. Enter Data into DB
                db_cursor.execute(
                    "INSERT INTO chat_logs (timestamp, username, message) VALUES (?, ?, ?)",
                    (current_time, username, message)
                )
                db_connection.commit()
                print(f"💬 [{username}]: {message}")
            except IndexError:
                continue

except KeyboardInterrupt:
    print("\n🛑 Stopped by user.")
finally:
    irc_socket.close()
    db_connection.close()
    print("🔌 All network and database connections safely closed.")
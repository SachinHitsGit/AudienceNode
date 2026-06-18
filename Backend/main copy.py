from fastapi import FastAPI, HTTPException  # FIXED spelling
from fastapi.middleware.cors import CORSMiddleware
import threading
from datetime import datetime

from twh_comm import run_analysis_pipeline
from twh_sponser import run_sponser_pipeline

app = FastAPI(title="Twitch Analytics Backend")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

state = {
    "is_polling": False,
    "start_time": None,
    "stop_time": None,
    "background_thread": None,
    "stop_event": None,
    "latest_results": {"message": "No metrics calculated yet. Run a session first."}
}

def dummy_irc_listener(stop_event):
    import time
    while not stop_event.is_set():
        time.sleep(0.5)

@app.get("/")
def index():
    return "welcome"

@app.get("/results")
def get_results():
    return state["latest_results"]  # FIXED: added missing 's'

@app.post("/poll/start")
def start_poll():
    if state["is_polling"]:
        raise HTTPException(status_code=400, detail="Polling is already active.")  # FIXED spelling
    
    state["stop_event"] = threading.Event()  # FIXED: Changed from threading.Thread to threading.Event()
    state["is_polling"] = True

    state["start_time"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    state["background_thread"] = threading.Thread(
        target=dummy_irc_listener,
        args=(state["stop_event"],),
        daemon=True
    )
    state["background_thread"].start()

    return {"status": "Polling started", "started_at": state["start_time"]}

@app.post("/poll/stop")
def stop_poll():
    if not state["is_polling"]:
        raise HTTPException(status_code=400, detail="No active poll running.")  # FIXED spelling
    
    state["stop_event"].set()
    if state["background_thread"]:
        state["background_thread"].join(timeout=5)  # FIXED: added missing 'd' to key name
    
    state["is_polling"] = False
    state["stop_time"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    print("Gathering metrics across both processing pipelines...")

    try:
        community_data = run_analysis_pipeline(state["start_time"], state["stop_time"])
        sponsor_data = run_sponser_pipeline(state["start_time"], state["stop_time"])

        state["latest_results"] = {
            "session_metadata": {
                "poll_start": state["start_time"],
                "poll_stop": state["stop_time"],
            },
            "community_insights": community_data,
            "sponsor_insights": sponsor_data
        }

    except Exception as e:
        state["latest_results"] = {"error": f"API pipeline execution failed: {str(e)}"}
        raise HTTPException(status_code=500, detail=str(e))  # FIXED spelling and detail argument name

    return {"status": "Processing complete", "stopped_at": state["stop_time"]}
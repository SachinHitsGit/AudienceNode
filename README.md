# AudienceNode 📡

![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)
![Backend: FastAPI](https://img.shields.io/badge/Backend-FastAPI-009688.svg)
![Frontend: React](https://img.shields.io/badge/Frontend-React-61DAFB.svg)

**AudienceNode** is a real-time, multi-threaded FastAPI & React pipeline. It ingests Twitch chat via raw IRC sockets, applies K-Means clustering to sentence embeddings, and groups unstructured text into semantic topics to deliver mathematically verified proof of audience engagement.

<img width="1920" height="1080" alt="image" src="https://github.com/user-attachments/assets/cfdf007c-788c-470f-b54b-bd87366d87f6" />


---

## 🚀 Core Features

* **Zero-Latency Ingestion:** Direct, multi-threaded connection to Twitch via IRC sockets.
* **Semantic Machine Learning:** Uses vector embeddings and K-Means clustering to statistically group chat messages rather than relying on simple keyword matching.
* **Engagement Verification:** Provides mathematically sound ROI (Return on Investment) metrics for sponsored segments by grouping and measuring actual audience sentiment.
* **Modern Dashboard:** A state-driven React frontend styled with Tailwind CSS v4 for real-time telemetry and cluster visualization.

---

## 🛠️ Technology Stack

**Backend**
* Python 3.10+
* FastAPI & Uvicorn
* Scikit-Learn (K-Means Clustering)
* SQLite (Ephemeral message buffering)

**Frontend**
* React 18
* Vite
* Tailwind CSS v4

---

## ⚙️ Quick Start Installation

### Prerequisites
* [Node.js](https://nodejs.org/) (v18+)
* Python (v3.10+)
* [Twitch CLI](https://dev.twitch.tv/docs/cli/)

### 1. Generate the Twitch Token
To read live chat, you need an OAuth token. Run this in your terminal:
```bash
twitch token -u -s "chat:read chat:edit"
```
Copy the generated `access_token`.

### 2. Configure the Backend
Open a terminal, navigate to the backend, create your environment, and add your credentials:
```bash
cd Backend
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```
Create a `.env` file in the `Backend/` directory:
```env
TWITCH_TOKEN=oauth:YOUR_COPIED_TOKEN_HERE
TWITCH_USERNAME=your_twitch_username
```

### 3. Configure the Frontend
Open a **second** terminal window and prepare the React dashboard:
```bash
cd Frontend
npm install
```

---

## 🏃‍♂️ Running the Engine

You must run both the backend API and the frontend dashboard simultaneously.

**Terminal 1 (Backend):**
```bash
cd Backend
source venv/bin/activate
uvicorn main:app --reload
```

**Terminal 2 (Frontend):**
```bash
cd Frontend
npm run dev
```

Navigate to `http://localhost:5173` in your web browser. Click **Start Tracking** to lock the IRC socket to your channel and begin buffering data. Click **Stop & Cluster** to run the ML pipeline and render the semantic groupings.

---

## 📄 License
This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

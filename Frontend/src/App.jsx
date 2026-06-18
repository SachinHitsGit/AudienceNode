import React, { useState, useEffect } from "react";
import ControlPanel from "./components/ControlPanel";
import ClusterCard from "./components/ClusterCard";

export default function App() {
  const [status, setStatus] = useState({
    is_listening: false,
    active_poll_id: null,
    buffer_size: 0,
  });
  const [pollData, setPollData] = useState(null);
  const [loading, setLoading] = useState(false);

  // Sync state with the backend status endpoint on mount
  useEffect(() => {
    fetchStatus();
    // Continually poll status every 3 seconds to update the buffer counter visually
    const interval = setInterval(fetchStatus, 3000);
    return () => clearInterval(interval);
  }, []);

  const fetchStatus = async () => {
    try {
      const res = await fetch("http://127.0.0.1:8000/status");
      const data = await res.json();
      setStatus(data);
    } catch (err) {
      console.error("Failed to fetch status matrix:", err);
    }
  };

  const startPoll = async () => {
    try {
      const res = await fetch("http://127.0.0.1:8000/poll/start", { method: "POST" });
      const data = await res.json();
      if (!data.error) {
        setPollData(null); // Wipe prior calculations card layout
        fetchStatus();
      }
    } catch (err) {
      console.error("Error running start tracking execution:", err);
    }
  };

  const stopPoll = async () => {
    setLoading(true);
    try {
      const res = await fetch("http://127.0.0.1:8000/poll/stop", { method: "POST" });
      const data = await res.json();
      if (!data.error) {
        setPollData(data);
        fetchStatus();
      }
    } catch (err) {
      console.error("Error executing stop and model vectorize clustering:", err);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="min-h-screen bg-slate-900 text-slate-100 font-sans p-4 sm:p-8 selection:bg-indigo-500 selection:text-white">
      <div className="max-w-7xl mx-auto">

        {/* Main Header Application Banner */}
        <header className="mb-8 border-b border-slate-800 pb-6">
          <h1 className="text-3xl font-extrabold tracking-tight bg-gradient-to-r from-indigo-400 to-violet-400 bg-clip-text text-transparent">
            Twitch Sponsor Analytics Engine
          </h1>
          <p className="text-sm text-slate-400 mt-1">
            Real-time multi-threaded ingestion, stream capture, and semantic density embedding maps.
          </p>
        </header>

        {/* Dashboard Control Interface */}
        <ControlPanel
          isListening={status.is_listening}
          activePollId={status.active_poll_id}
          bufferSize={status.buffer_size}
          onStart={startPoll}
          onStop={stopPoll}
        />

        {/* Inference / Loader Interface states */}
        {loading && (
          <div className="text-center py-12 bg-slate-800/30 border border-dashed border-slate-700 rounded-xl">
            <div className="inline-block animate-spin rounded-full h-8 w-8 border-4 border-indigo-500 border-t-transparent mb-3" />
            <p className="text-slate-400 text-sm font-mono">Running vector calculations & centroid discovery clustering...</p>
          </div>
        )}

        {/* Cluster Results Grid Rendering Block */}
        {pollData && !loading && (
          <div>
            <div className="mb-6 flex justify-between items-end">
              <div>
                <h2 className="text-xl font-bold text-white">Calculated Semantic Groupings</h2>
                <p className="text-xs text-slate-400 mt-0.5">
                  Interval: {pollData.start_time} ➔ {pollData.stop_time}
                </p>
              </div>
              <span className="text-xs font-mono text-slate-500">Poll Session ID: #{pollData.poll_id}</span>
            </div>

            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
              {pollData.clusters?.map((cluster) => (
                <ClusterCard key={cluster.cluster_id} cluster={cluster} />
              ))}
            </div>
          </div>
        )}

      </div>
    </div>
  );
}
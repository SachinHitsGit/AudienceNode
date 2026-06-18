import CustomButton from "./CustomButton";

export default function ControlPanel({ isListening, activePollId, bufferSize, onStart, onStop }) {
    return (
        <div className="bg-slate-800 border border-slate-700 rounded-xl p-6 shadow-xl mb-8">
            <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-6">

                {/* State Identifiers */}
                <div>
                    <h2 className="text-xl font-bold text-white mb-2">Pipeline Controller</h2>
                    <div className="flex flex-wrap gap-3 items-center text-sm text-slate-300">
                        <span className="flex items-center gap-2">
                            <span className={`w-3 h-3 rounded-full ${isListening ? "bg-emerald-500 animate-pulse" : "bg-slate-500"}`} />
                            Status: <strong className={isListening ? "text-emerald-400" : "text-slate-400"}>{isListening ? "Streaming Active" : "Idle"}</strong>
                        </span>
                        {isListening && (
                            <>
                                <span className="text-slate-600">|</span>
                                <span>Active ID: <strong className="text-indigo-400">#{activePollId}</strong></span>
                                <span className="text-slate-600">|</span>
                                <span>Buffer Size: <strong className="text-amber-400">{bufferSize} lines</strong></span>
                            </>
                        )}
                    </div>
                </div>

                {/* Action Triggers */}
                <div className="flex gap-4">
                    <CustomButton
                        label="Start Tracking"
                        action={onStart}
                        variant="primary"
                        disabled={isListening}
                    />
                    <CustomButton
                        label="Stop & Cluster"
                        action={onStop}
                        variant="danger"
                        disabled={!isListening}
                    />
                </div>

            </div>
        </div>
    );
}
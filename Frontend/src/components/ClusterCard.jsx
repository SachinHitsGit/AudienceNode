import React from "react";

export default function ClusterCard({ cluster }) {
    return (
        <div className="bg-slate-800 border border-slate-700 rounded-xl p-6 shadow-lg flex flex-col h-full">

            {/* Header Info */}
            <div className="flex justify-between items-start border-b border-slate-700 pb-4 mb-4">
                <div>
                    <h3 className="text-lg font-bold text-slate-100">
                        Topic Cluster #{cluster.cluster_id}
                    </h3>
                    <p className="text-xs text-slate-400 mt-0.5">Statistical Representative Exemplars</p>
                </div>
                <span className="bg-indigo-500/10 text-indigo-400 border border-indigo-500/20 text-xs font-bold px-2.5 py-1 rounded-full">
                    Size: {cluster.size} lines
                </span>
            </div>

            {/* Exemplar Message Iteration List */}
            <div className="space-y-3 overflow-y-auto flex-grow max-h-72 pr-1 custom-scrollbar">
                {cluster.exemplars.map((ex, index) => (
                    <div
                        key={index}
                        className="bg-slate-900/60 border border-slate-700/50 rounded-lg p-3 transition-hover hover:border-slate-600"
                    >
                        <div className="flex justify-between items-center mb-1">
                            <span className="text-xs font-bold text-indigo-400">
                                @{ex.username}
                            </span>
                        </div>
                        <p className="text-sm text-slate-300 font-mono leading-relaxed break-words">
                            "{ex.message}"
                        </p>
                    </div>
                ))}
            </div>

        </div>
    );
}
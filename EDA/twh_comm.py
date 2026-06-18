import sqlite3
import numpy as np
from sentence_transformers import SentenceTransformer
from sklearn.decomposition import PCA
from sklearn.cluster import KMeans
import matplotlib.pyplot as plt

# ── CONFIG ─────────────────────────────────────────────────────────────────────

DB_PATH      = "/home/sachinkumar/Desktop/sponser_proof_gen/twitch_chat.db"
POLL_START   = "2024-01-01 00:00:00"
POLL_STOP    = "2099-01-01 00:00:00"
MAX_K        = 12   # elbow search upper bound
TOP_N        = 5    # exemplars to show per cluster


# ── STEP 1: FETCH MESSAGES IN POLL WINDOW ─────────────────────────────────────

def fetch_messages(db_path, start, stop):
    conn   = sqlite3.connect(db_path)
    cursor = conn.cursor()
    cursor.execute("""
        SELECT username, message FROM chat_logs
        WHERE timestamp BETWEEN ? AND ?
        AND message IS NOT NULL
        AND TRIM(message) != ''
    """, (start, stop))
    rows = cursor.fetchall()
    conn.close()

    usernames = [r[0] for r in rows]
    messages  = [r[1] for r in rows]
    print(f"✅ Fetched {len(messages)} messages from poll window.")
    return usernames, messages


# ── STEP 2: EMBED ──────────────────────────────────────────────────────────────

def embed_messages(messages):
    print("🔢 Computing sentence embeddings...")
    model      = SentenceTransformer("all-MiniLM-L6-v2")
    embeddings = model.encode(messages, show_progress_bar=True)
    print(f"   → Embedding shape: {embeddings.shape}")
    return embeddings


# ── STEP 3: PCA ────────────────────────────────────────────────────────────────

def reduce_with_pca(embeddings, n_components=3):
    print(f"📉 Reducing dimensions to {n_components}D with PCA...")
    pca        = PCA(n_components=n_components)
    reduced    = pca.fit_transform(embeddings)
    explained  = pca.explained_variance_ratio_.sum() * 100
    print(f"   → Variance retained: {explained:.1f}%")
    return reduced


# ── STEP 4: ELBOW METHOD → AUTO PICK K ────────────────────────────────────────

def find_optimal_k(coordinates, max_k=12, plot=True):
    n_samples  = len(coordinates)
    upper      = min(max_k, n_samples - 1)   # can't have more clusters than samples
    k_range    = range(2, upper + 1)
    inertias   = []

    print(f"\n📊 Running elbow method (K=2 to K={upper})...")
    for k in k_range:
        km = KMeans(n_clusters=k, random_state=42, n_init="auto")
        km.fit(coordinates)
        inertias.append(km.inertia_)
        print(f"   K={k:>2}  inertia={km.inertia_:.4f}")

    # Auto-detect elbow: largest drop in inertia reduction rate
    drops = [inertias[i] - inertias[i + 1] for i in range(len(inertias) - 1)]
    best_k = list(k_range)[drops.index(max(drops)) + 1]
    print(f"\n✅ Auto-selected K = {best_k} (sharpest elbow)")

    if plot:
        plt.figure(figsize=(9, 5))
        plt.plot(list(k_range), inertias, marker="o", linewidth=2, color="steelblue")
        plt.axvline(x=best_k, color="red", linestyle="--", label=f"Elbow at K={best_k}")
        plt.title("Elbow Method — Optimal K Selection")
        plt.xlabel("Number of Clusters (K)")
        plt.ylabel("Inertia")
        plt.xticks(list(k_range))
        plt.legend()
        plt.grid(True, linestyle="--", alpha=0.5)
        plt.tight_layout()
        plt.show()

    return best_k


# ── STEP 5: K-MEANS CLUSTERING ────────────────────────────────────────────────

def cluster(coordinates, k):
    print(f"\n🔵 Running K-Means with K={k}...")
    km             = KMeans(n_clusters=k, random_state=42, n_init="auto")
    cluster_labels = km.fit_predict(coordinates)
    centroids      = km.cluster_centers_
    print(f"   → Done. {k} clusters formed.")
    return cluster_labels, centroids


# ── STEP 6: EXTRACT CENTROID EXEMPLARS ────────────────────────────────────────

def extract_exemplars(coordinates, cluster_labels, centroids, usernames, messages, top_n=5):
    results = []
    n_clusters = len(centroids)

    for cluster_id in range(n_clusters):
        centroid         = centroids[cluster_id]
        cluster_indices  = np.where(cluster_labels == cluster_id)[0]
        cluster_coords   = coordinates[cluster_indices]

        # Euclidean distance from each point to its centroid
        distances        = np.linalg.norm(cluster_coords - centroid, axis=1)
        closest_relative = np.argsort(distances)[:top_n]
        closest_master   = cluster_indices[closest_relative]

        exemplars = []
        for idx in closest_master:
            exemplars.append({
                "username": usernames[idx],
                "message":  messages[idx].strip().replace("\n", " ")
            })

        results.append({
            "cluster_id": cluster_id,
            "size":       int(len(cluster_indices)),
            "exemplars":  exemplars,
        })

    return results


# ── STEP 7: PRINT RESULTS ─────────────────────────────────────────────────────

def print_clusters(clusters):
    print("\n" + "=" * 60)
    print("  COMMUNITY TOPIC CLUSTERS — CENTROID EXEMPLARS")
    print("=" * 60)

    for c in clusters:
        pct = (c["size"] / sum(x["size"] for x in clusters)) * 100
        print(f"\n📁 CLUSTER {c['cluster_id']}  ({c['size']} messages, {pct:.1f}% of chat)")
        print("-" * 60)
        for i, ex in enumerate(c["exemplars"], 1):
            msg = ex["message"]
            msg = msg if len(msg) < 120 else msg[:117] + "..."
            print(f"  {i}. [{ex['username']}]: {msg}")


# ── RUN ────────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    usernames, messages = fetch_messages(DB_PATH, POLL_START, POLL_STOP)

    if len(messages) < 4:
        print("⚠️  Not enough messages to cluster. Add more data first.")
        exit()

    embeddings  = embed_messages(messages)
    coordinates = reduce_with_pca(embeddings, n_components=0.85)
    best_k      = find_optimal_k(coordinates, max_k=MAX_K, plot=True)
    labels, centroids = cluster(coordinates, best_k)
    clusters    = extract_exemplars(coordinates, labels, centroids, usernames, messages, TOP_N)

    print_clusters(clusters)
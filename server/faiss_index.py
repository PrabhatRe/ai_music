import os
import numpy as np
import faiss

# --- Paths ---
EMBEDDINGS_FILE = "../embeddings/embeddings.npy"
FAISS_INDEX_FILE = "../embeddings/faiss.index"

# --- Load embeddings ---
data = np.load(EMBEDDINGS_FILE, allow_pickle=True).item()
songs = data["songs"]
embeddings = np.array(data["embeddings"]).astype("float32")

# --- Create FAISS index ---
dim = embeddings.shape[1]
index = faiss.IndexFlatL2(dim)
index.add(embeddings)

# --- Ensure folder exists ---
os.makedirs(os.path.dirname(FAISS_INDEX_FILE), exist_ok=True)

# --- Save index to disk ---
faiss.write_index(index, FAISS_INDEX_FILE)

print(f"[INFO] FAISS index created with {len(songs)} songs and saved to {FAISS_INDEX_FILE}")

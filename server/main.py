# server/main.py
import os
import numpy as np
import faiss
import requests
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware

# --- Configs ---
MUSIC_DIR = "../music"
EMBEDDING_FILE = "../embeddings/embeddings.npy"
FAISS_INDEX_FILE = "../embeddings/faiss.index"

NAVIDROME_HOST = "http://localhost:4533"
USER = "prabhat"
PASS = "prabhat25"
PLAYLIST_ID = "1"

# --- Load embeddings and FAISS ---
data = np.load(EMBEDDING_FILE, allow_pickle=True).item()
songs = data["songs"]
embeddings = np.array(data["embeddings"]).astype("float32")

index = faiss.read_index(FAISS_INDEX_FILE)

# --- FastAPI ---
app = FastAPI()
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"]
)

# --- Navidrome helpers ---
def start_playback(song_id):
    url = f"{NAVIDROME_HOST}/rest/startPlayback.view"
    params = {"u": USER, "p": PASS, "id": song_id}
    try:
        r = requests.get(url, params=params)
        return r.status_code == 200
    except:
        return False

def add_to_playlist(song_id):
    url = f"{NAVIDROME_HOST}/rest/updatePlaylist.view"
    params = {"u": USER, "p": PASS, "id": PLAYLIST_ID, "songId": song_id}
    try:
        r = requests.get(url, params=params)
        return r.status_code == 200
    except:
        return False

# --- Dummy mapping (for MP3s) ---
# You can later integrate Navidrome song IDs properly
song_mapping = {song: song for song in songs}  # song filename -> "song id"

# --- Recommendation ---
@app.get("/recommend")
def recommend(song: str, top_n: int = 5):
    if song not in songs:
        raise HTTPException(status_code=404, detail="Song not found")

    i = songs.index(song)
    query_vec = embeddings[i].reshape(1, -1)
    distances, indices = index.search(query_vec, top_n + 1)
    recommended_songs = [songs[idx] for idx in indices[0] if idx != i][:top_n]

    recommended_ids = [song_mapping[s] for s in recommended_songs]

    if not recommended_ids:
        raise HTTPException(status_code=404, detail="No playable recommendations found")

    # Autoplay first song
    start_playback(recommended_ids[0])
    # Queue the rest
    for sid in recommended_ids[1:]:
        add_to_playlist(sid)

    return {"query": song, "recommendations": recommended_songs}

# --- Optional root ---
@app.get("/")
def root():
    return {"status": "Server running. Use /recommend?song=<song_name>&top_n=<N>"}

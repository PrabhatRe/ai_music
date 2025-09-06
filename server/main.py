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

JELLYFIN_HOST = "http://localhost:8096"
API_KEY = "YOUR_JELLYFIN_API_KEY"  # Replace with your Jellyfin API key
PLAYLIST_ID = "1"  # Replace with your playlist ID
MUSIC_FOLDER_ID = "YOUR_MUSIC_FOLDER_ID"  # Jellyfin music library ID

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

# --- Jellyfin helpers ---
def get_song_mapping():
    """
    Generate a mapping of song filename -> Jellyfin item ID.
    """
    headers = {"X-Emby-Token": API_KEY}
    mapping = {}
    url = f"{JELLYFIN_HOST}/Users/Me/Items?ParentId={MUSIC_FOLDER_ID}&IncludeItemTypes=Audio&Recursive=true"

    try:
        r = requests.get(url, headers=headers)
        r.raise_for_status()
        items = r.json().get("Items", [])
        for item in items:
            filename = item["Name"]
            item_id = item["Id"]
            mapping[filename] = item_id
    except Exception as e:
        print("Error fetching items from Jellyfin:", e)

    return mapping

def start_playback(item_id):
    """
    Start playback of the first recommended song on Jellyfin.
    """
    url = f"{JELLYFIN_HOST}/Sessions/Playing"
    headers = {"X-Emby-Token": API_KEY}
    data = {"ItemIds": [item_id], "StartPositionTicks": 0}
    try:
        r = requests.post(url, headers=headers, json=data)
        return r.status_code in [200, 204]
    except:
        return False

def add_to_playlist(item_id):
    """
    Add a song to a Jellyfin playlist.
    """
    url = f"{JELLYFIN_HOST}/Playlists/{PLAYLIST_ID}/Items"
    headers = {"X-Emby-Token": API_KEY}
    data = {"ItemIds": [item_id]}
    try:
        r = requests.post(url, headers=headers, json=data)
        return r.status_code in [200, 204]
    except:
        return False

# --- Generate song mapping ---
song_mapping = get_song_mapping()

# --- Recommendation endpoint ---
@app.get("/recommend")
def recommend(song: str, top_n: int = 5):
    if song not in songs:
        raise HTTPException(status_code=404, detail="Song not found")

    # Search FAISS for similar songs
    i = songs.index(song)
    query_vec = embeddings[i].reshape(1, -1)
    distances, indices = index.search(query_vec, top_n + 1)
    recommended_songs = [songs[idx] for idx in indices[0] if idx != i][:top_n]

    # Map filenames to Jellyfin item IDs
    recommended_ids = [song_mapping.get(s) for s in recommended_songs if s in song_mapping]

    if not recommended_ids:
        raise HTTPException(status_code=404, detail="No playable recommendations found")

    # Autoplay first song
    start_playback(recommended_ids[0])
    # Queue the rest in playlist
    for sid in recommended_ids[1:]:
        add_to_playlist(sid)

    return {"query": song, "recommendations": recommended_songs}

# --- Optional root ---
@app.get("/")
def root():
    return {"status": "Server running. Use /recommend?song=<song_name>&top_n=<N>"}

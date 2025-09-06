import os
import librosa
import numpy as np

MUSIC_DIR = "../music"
EMBEDDING_FILE = "../embeddings/embeddings.npy"

songs = []
embeddings = []

for file in sorted(os.listdir(MUSIC_DIR)):
    if file.endswith(".mp3"):
        path = os.path.join(MUSIC_DIR, file)
        y, sr = librosa.load(path, duration=30)  # first 30s
        mfcc = librosa.feature.mfcc(y=y, sr=sr)
        emb = mfcc.mean(axis=1)
        songs.append(file)
        embeddings.append(emb)

os.makedirs("../embeddings", exist_ok=True)
np.save(EMBEDDING_FILE, {"songs": songs, "embeddings": embeddings})

print(f"[INFO] Saved embeddings for {len(songs)} songs to {EMBEDDING_FILE}")

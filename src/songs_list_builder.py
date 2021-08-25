import json
import os

all_songs = {}
spotify_dataset_path = 'data/spotify_million_playlist_dataset/'


# Add all songs from a Spotify slice file (from dataset) to all_songs.json
def add_all_songs_from_file(path):
    with open(path) as f:
        data = json.load(f)
        
    for playlist in data['playlists']:
        for track in playlist['tracks']:
            track_id = track['track_uri'].partition('spotify:track:')[-1]
            artist_id = track['artist_uri'].partition('spotify:artist:')[-1]
            if track_id not in all_songs:
                all_songs[track_id] = {
                    'track_name': track['track_name'], 
                    'artist_name': track['artist_name'], 
                    'artist_id': artist_id
                }

for slice_file in os.listdir(spotify_dataset_path):
    add_all_songs_from_file(spotify_dataset_path + slice_file)
    print(f'added songs from {slice_file}')
with open('data/songs_dataset.json', 'w') as f:
    json.dump(all_songs, f)
    print(f'\nadded {len(all_songs)} songs')

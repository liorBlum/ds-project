import aiohttp
import asyncio
import time
import json
from lyrics_scraper import url, lyrics
import unicodedata
import re

asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())

all_urls = []
all_require_search = []
all_lyrics = {}

# Build Genius URLs dictionary

start_time = time.time()

def parse_name(name):
    s = unicodedata.normalize('NFKD', name).encode('ascii','ignore').decode('utf8')
    s = re.search(r'([^()\[\]-]*)', s).group(1).strip().replace(' ', '-').replace('&', 'and')
    return re.sub('[^a-zA-Z0-9_\-]', '', s)

currently_have = 0
with open('./data/all_songs.json', 'r') as songs_file:
    with open('./data/lyrics1-10000.json', 'r') as lyrics_file:
        all_songs = json.load(songs_file)
        all_lyrics = json.load(lyrics_file)
        assert type(all_lyrics) == dict
        assert type(all_songs) == dict
        counter = 0
        for track_id, track_data in all_songs.items():
            # Limit number of songs
            if counter >= 10000:
                break
            counter += 1
            # Don't fetch lyrics we already have
            if all_lyrics.get(track_id):
                currently_have += 1
                continue
            parsed_track_name = parse_name(track_data['track_name'])
            parsed_artist_name = parse_name(track_data['artist_name'])
            if parsed_artist_name and parsed_track_name:
                all_urls.append((track_id, track_data, 
                    f'https://genius.com/{parsed_artist_name}-{parsed_track_name}-lyrics'))
                
            else:
                all_require_search.append((track_id, track_data, ''))
            

print(f'len(all_urls) equals {len(all_urls)}')
print("--- URLs list building took %s seconds ---" % (time.time() - start_time))

all_require_search += all_urls # DEBUG


# Build lyrics list with asynchronous HTTP requests to genius.com

async def search_url(session, track_id, track_data):
    try:
        # search_term = f"{track_data['track_name']} {track_data['artist_name']}".strip()
        search_term = f"{track_data['track_name']}".strip()
        path = 'https://genius.com/api/search/multi'
        params_ = {'q': search_term}
        async with session.get(path, timeout=5, params=params_) as resp:
            if (resp.status == 200):
                resp = await resp.json()
                return (track_id, track_data, url(resp['response'], track_data['track_name']))
            
            else:
                print(f"received status {resp.status} for {track_data['track_name']}")
                return (track_id, track_data, None)
    except Exception as e:
        print(f'Received error {type(e)} for {url}')
        # raise e
        return (track_id, track_data, None)

async def get_lyrics(session, url, track_id, track_name):
    try:
        async with session.get(url, timeout=10) as resp:
            if (resp.status == 200):
                lyrics_html = await resp.text()
                return (track_id, track_name + '\n' + lyrics(lyrics_html, True))
            else:
                print(f'received status {resp.status} for {url}')
                return (track_id, None)
    except Exception as e:
        print(f'Received error {type(e)} for {url}')
        # raise e
        return (track_id, None)

new_urls = []
songs_lyrics_list = []

async def add_to_urls_list(tracks_list, songs_offsets=(0, None)):
    global new_urls

    async with aiohttp.ClientSession() as session:
        tasks = []
        counter = 0
        print(f'searching URLs of songs {songs_offsets[0]}:{songs_offsets[1]}')
        for track_id, track_data, _ in tracks_list[songs_offsets[0]:songs_offsets[1]]:
            # if counter >= 1:
            #     break
            tasks.append(asyncio.ensure_future(search_url(session, track_id, track_data)))
            # counter += 1

        new_urls += await asyncio.gather(*tasks)

async def add_to_lyrics_list(urls_list, songs_offsets=(0, None)):
    global songs_lyrics_list

    async with aiohttp.ClientSession() as session:
        tasks = []
        counter = 0
        print(f'retrieving lyrics of songs {songs_offsets[0]}:{songs_offsets[1]}')
        for track_id, track_data, url in urls_list[songs_offsets[0]:songs_offsets[1]]:
            # if counter >= 1:
            #     break
            tasks.append(asyncio.ensure_future(get_lyrics(session, url, track_id, track_data['track_name'])))
            # counter += 1

        songs_lyrics_list += await asyncio.gather(*tasks)
        

# total_songs_num = len(all_urls) # DEBUG
total_songs_num = len(all_require_search)
songs_at_each_interval = 100

start_time = time.time()
for i in range(0, total_songs_num, songs_at_each_interval):
    asyncio.run(add_to_urls_list(all_require_search, (i, i + songs_at_each_interval)))
    time.sleep(0.2)
print("--- Missing songs search took %s seconds ---" % (time.time() - start_time))
new_urls = [(track_id, track_data, track_url) for (track_id, track_data, track_url) in new_urls if track_url]
print(f'found {len(new_urls)} URLS of missing songs')

start_time = time.time()
for i in range(0, total_songs_num, songs_at_each_interval):
    asyncio.run(add_to_lyrics_list(new_urls, (i, i + songs_at_each_interval)))
    time.sleep(0.2)
end_time = time.time()
print("--- Missing lyrics retrieval through search took %s seconds ---" % (end_time - start_time))

# start_time = time.time()
# for i in range(0, total_songs_num, songs_at_each_interval):
#     asyncio.run(add_to_lyrics_list(all_urls, (i, i + songs_at_each_interval)))
#     time.sleep(0.2)
# end_time = time.time()

# print("--- Lyrics retrieval took %s seconds ---" % (end_time - start_time))


# songs_lyrics_list = [(track_id, lyrics) for (track_id, lyrics) in songs_lyrics_list if lyrics]
# print(f'finished lyrics retrieval of {len(songs_lyrics_list)} songs')

start_time = time.time()
file_path = './data/lyrics1-10000.json'
with open(file_path, 'w') as f:
    all_lyrics.update({track_id: lyrics for (track_id, lyrics) in songs_lyrics_list})
    json.dump(all_lyrics, f)
print(f"added lyrics for {len(songs_lyrics_list)} songs to {file_path}")
print("--- Lyrics file writing took %s seconds ---" % (end_time - start_time))

#export SPOTIPY_CLIENT_ID='7df77099461e4a33a3ccd1471a5e66b6'
#export SPOTIPY_CLIENT_SECRET='80a339be93c74bd89a53a160b91f46bb'
#export SPOTIPY_REDIRECT_URI='http://localhost:8070'

import mutagen as mg
import eyed3, re, spotipy
import pdb, sys
from spotipy.oauth2 import SpotifyOAuth
from compare import evaluate
from datetime import datetime

print('Connecting to Spotify API...')
sp = spotipy.Spotify(auth_manager=SpotifyOAuth(scope='playlist-modify-private', username='louie.gabriel@gmail.com'))
print('Done.')

def mp3Handler(path):
	data = eyed3.load(path)
	return {'title': str(data.tag.title or ''),
			'artist': str(data.tag.artist or ''),
			'album artist': str(data.tag.album_artist or ''),
			'album': str(data.tag.album or '')}
	
def flacHandler(path):
	data = mg.File(path)
	return {'title': data.get('title', [''])[0],
			'artist': data.get('artist', [''])[0],
			'album artist': data.get('albumartist', [''])[0],
			'album': data.get('album', [''])[0]}

handlers = {
	'.mp3': mp3Handler,
	'.MP3': mp3Handler,
	'.flac': flacHandler,
	'.FLAC': flacHandler
}

tolerances = {
	'initial': 0.75,
	'withoutAlbum': 0.6,
	'withoutAlbumOrAlbumArtist': 0.6
}

def search(searchString, trackInfo):
	results = sp.search(searchString)
	candidates = []
	for res in results['tracks']['items']:
		candidate = {}
		candidate['title'] = res['name']
		candidate['album'] = res['album']['name']
		candidate['album artists'] = list(map(lambda x: x['name'], res['album']['artists']))
		candidate['artists'] = list(map(lambda x: x['name'], res['artists']))
		candidate['similarity'] = evaluate(candidate, trackInfo)
		candidate['uri'] = res['uri']
		candidates.append(candidate)
	return sorted(candidates, key=lambda x: x['similarity'], reverse=True)

def buildPlaylist(userId, playlistId, uris, n):
	#If we are creating a massive playlist
	#we have to do it bit by bit to avoid
	#the API cap
	i = 0
	while i < len(uris):
		sp.user_playlist_add_tracks(
			user=userId,
			playlist_id=playlistId,
			tracks=uris[i:i+n])
		i += n


def main():
	try:
		pl = open("/home/louie/other/Acid Rain.m3u").read().split("\n")[0:-1]
	except FileNotFoundError:
		print('Could not open playlist file ' + 'bla bla')
		sys.exit()
	except Exception:
		print('Unexpected error: ', sys.exc_info()[0])
		sys.exit()

	mainRegex = "Music\\\\(.*?)\\\\(.*?)\\\\(.*?)$"
	found = []	#Spotipy documentation incorrectly states it should be ID
	missing = []
	for track in pl:
		try:
			result = re.findall(mainRegex, track)
			if result == []:
				print('Could not match any groups in string: ' + track)
				continue
			g = result[0]
			if len(g) != 3:
				print('Could not match some groups in string: ' + track)
				continue

			#Want to now map our captured groups to parts of the path where we think the actual tracks live.
			path = f'/home/louie/SD/Music/{g[0]}/{g[1]}/{g[2]}'
			handlerFound = False
			for extension, handler in handlers.items():
				if g[2].endswith(extension):
					handlerFound = True
					trackInfo = handler(path)
					break
			if not handlerFound:
				print('No support for file type of: ' + track)
				continue
			
			searchString = ' '.join(filter(None, trackInfo.values()))
			candidates = search(searchString, trackInfo)
			
			if candidates and candidates[0]['similarity'] > tolerances['initial']:
				found.append(candidates[0])
			else:
				#We need to remove some search terms and try again
				#The album is the most likely culprit
				modified = trackInfo.copy()
				del modified['album']
				searchString = ' '.join(filter(None, modified.values()))
				candidates = search(searchString, modified)
				if candidates and candidates[0]['similarity'] > tolerances['withoutAlbum']:
					found.append(candidates[0])
				else:
					#Now try scrapping the album artist too
					del modified['album artist']
					searchString = ' '.join(filter(None, modified.values()))
					candidates = search(searchString, modified)
					if candidates and candidates[0]['similarity'] > tolerances['withoutAlbumOrAlbumArtist']:
						print(candidates[0])
						found.append(candidates[0])
					else:
						print("Can't be confident we've found track " + track)
						missing.append(track)
		except FileNotFoundError:
			print('Could not find file ' + track)
			missing.append(track)
			continue
		except Exception:
			print('Unexpected error: ', sys.exc_info()[0])
			missing.append(track)
			continue
		
	
	print(missing)
	uris = list(map(lambda t: t['uri'], found))
	userId = sp.me()['id']
	targetPlaylist = sp.user_playlist_create(
		user=userId, 
		name='TEST PL: ' + datetime.now().strftime('%H:%M:%S'), 
		public=False, 
		description='')
	buildPlaylist(userId, targetPlaylist['id'], uris, 50)

		



main()
#export SPOTIPY_CLIENT_ID='7df77099461e4a33a3ccd1471a5e66b6'
#export SPOTIPY_CLIENT_SECRET='80a339be93c74bd89a53a160b91f46bb'
#export SPOTIPY_REDIRECT_URI='http://localhost:8070'

import mutagen as mg
import eyed3, re, spotipy
import pdb, sys, logging, configparser
from spotipy.oauth2 import SpotifyOAuth
from compare import evaluate
from datetime import datetime
from tqdm import tqdm



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

profileLocation='exporter.profile'

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

def prompt(string, default):
	if not default:
		i = ''
		while i == '':
			i = input(string)
		return i
	else:
		i = input('(' + default + ') ' + string)
		return default if i == '' else i

def main():
	profile = configparser.ConfigParser()
	profile.read(profileLocation)
	if 'default' in profile:
		defaultPLFile = profile['default']['previousPlaylistFile'] if 'previousPlaylistFile' in profile['default'] else None
		defaultRegex = profile['default']['readRegex'] if 'readRegex' in profile['default'] else None
		defaultFileLoc = profile['default']['fileLocation'] if 'fileLocation' in profile['default'] else None
		defaultPlName = profile['default']['newPlaylistName'] if 'newPlaylistName' in profile['default'] else None
	else:
		defaultPLFile = None
		defaultRegex = None
		defaultFileLoc = None
		defaultPlName = None
	
	#There is definitely danger in doing it this way with the regex thing...
	#Could climb the file tree etc
	#I think for these purposes though, we don't care
	PLFile = prompt('Playlist file: ', defaultPLFile)
	mainRegex = prompt('Regex for reading the playlist file: ', defaultRegex)
	pathSkeleton = prompt('Path to tracks (array g holds the captured groups): ', defaultFileLoc)
	newPlName = prompt('Name for the Spotify playlist: ', defaultPlName)
	print()



	try:
		pl = open(PLFile).read().split("\n")[0:-1]
	except FileNotFoundError:
		print('Could not open playlist file ' + PLFile)
		logging.critical('Could not open playlist file ' + PLFile)
		sys.exit()
	except Exception:
		logging.critical('Unexpected error: %s', sys.exc_info()[0])
		sys.exit()

	print('Processing playlist file...')
	found = []	#Spotipy documentation incorrectly states it should be IDs, think it should
				#be URIs
	missing = []
	for track in tqdm(pl):
		try:
			logging.info('Processing %s', track)
			result = re.findall(mainRegex, track)
			if result == [] or result[0] == ():
				logging.error('Could not match any groups in string: %s', track)
				continue
			g = result[0]
			#Check we match every group?

			#Want to now map our captured groups to parts of the path where we think the actual tracks live.
			path = pathSkeleton
			for index, group in enumerate(g):
				path = re.compile(r'\{g\[' + str(index) + r'\]\}').sub(group, path)

			handlerFound = False
			for extension, handler in handlers.items():
				if g[-1].endswith(extension):
					handlerFound = True
					trackInfo = handler(path)
					break
			if not handlerFound:
				logging.error('No support for file type of: %s', track)
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
						found.append(candidates[0])
					else:
						logging.warning("Can't be confident we've found track %s", track)
						missing.append(track)
		except FileNotFoundError:
			logging.warning('Could not find file %s', track)
			missing.append(track)
			continue
		except Exception:
			logging.error('Unexpected error: %s', sys.exc_info()[0])
			missing.append(track)
			continue
		
	try:
		print('Done. The following tracks could not be found and will have to be added manually: ')
		print(*missing, sep='\n')
		uris = list(map(lambda t: t['uri'], found))
		userId = sp.me()['id']
		targetPlaylist = sp.user_playlist_create(
			user=userId, 
			name=newPlName, 
			public=False, 
			description='')
		print('Playlist ' + newPlName + ' created')
		logging.info('Playlist %s created', newPlName)
		buildPlaylist(userId, targetPlaylist['id'], uris, 50)
		print('Playlist populated')
		logging.info('Playlist populated')

		#Cleanup
		profile['default']['previousPlaylistFile'] = PLFile
		profile['default']['readRegex'] = mainRegex
		profile['default']['fileLocation'] = pathSkeleton
		profile['default']['newPlaylistName'] = newPlName
		with open(profileLocation, 'w') as confFile:
			profile.write(confFile)
	except Exception:
		print('Unexpected Spotipy errror: ', sys.exc_info()[0])
		sys.exit()

		

logFileName = 'spotify_playlist_import_log_' + datetime.now().strftime('%H:%M:%S') + '.log'
logging.basicConfig(format='%(levelname)s:%(message)s', 
		filename=logFileName,
		level=logging.INFO)
print('Log file set to ', logFileName)
print('Connecting to Spotify API...')
logging.info('Connecting to Spotify API')
sp = spotipy.Spotify(auth_manager=SpotifyOAuth(scope='playlist-modify-private', username='louie.gabriel@gmail.com'))
print('Done.')
logging.info('Done')
main()
print('Reminder: log file at ', logFileName)
# Spotify Local Playlist Importer

I have almost 400 gig of offline music, and a couple of *enormous* offline playlists that I fancied putting into Spotify so I could let friends collaborate on them. I also had a spare 24hrs. This is the result.

Lots of love to the guys maintaining the following projects!

* https://github.com/plamere/spotipy
* https://github.com/quodlibet/mutagen
* https://github.com/nicfit/eyeD3
* https://github.com/tqdm/tqdm

This script works by grabbing the metadata from your local files, trying a couple of different search terms against Spotify's database, and having a guess about whether we have a good enough match. I haven't spent that much time tweaking how it picks the songs to use, as they were good enough to grab all but a few of the tracks i needed copying - feel free to fiddle with the tolerances if they aren't where you think they should be. There are also exponents in `compare.py`, which you may disagree with me on, which weight the contribution of a closely matching 'title' field, say, should have on whether we think the two songs are the same. Again, change these at will.


## To run this:
I may package this and pretty it up by changing the login landing page at some point in the future if I can be bothered, but for now, you're going to need the four above packages installed. At the time of writing, I am using versions:

* Spotipy: 2.13.0
* Mutagen: 1.44.0
* eyeD3: 0.9.5
* tqdm: 4.46.1

Everything else is standard library. 

__I am basically assuming no one cares enough to grab the API information here. Please don't abuse this, it just makes for more work if anyone else wants to use it.__

So to run, call three lines:
```
export SPOTIPY_CLIENT_ID='xxx'
export SPOTIPY_CLIENT_SECRET='xxx'
export SPOTIPY_REDIRECT_URI='http://localhost:8070'
```

Where the ID and Secret are as given in the top two lines of playlist_import.py. Then just run (in the same directory as `importer.profile` unless you want it creating a new one)
```
python playlist_import.py
```
and follow the instructions within. It will help to understand regex.
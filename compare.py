from difflib import SequenceMatcher as seqm

appendages = ['remastered', 'remaster', 'original', 'deluxe', 'single', 'radio', 'version', 'edition']

def straightCompare(a, b):
    if a is not None and a is not '' and b is not None and b is not '':
    	return seqm(None, a.lower(), b.lower()).ratio()
    else:
        return 1

def appendCompare(a, b):
    if a is not None and a is not '' and b is not None and b is not '':
        comparisons = [(a, b)]
        for c in appendages:
            comparisons.append((a + ' ' + c, b))
            comparisons.append((a, b + ' ' + c))
        return max(list(map(lambda x: straightCompare(x[0], x[1]), comparisons)))
    else:
        return 1


def evaluate(candidate, track):
    #Think we basically want a running product
    #This could maybe be an avenue for exploring
    #some ML techniques though....

    #For now however:
    #print(track)
    #print(candidate)
    similarity = 1.0
    similarity *= appendCompare(candidate['title'], track.get('title'))**1
    similarity *= appendCompare(candidate['album'], track.get('album'))**1
    similarity *= straightCompare(candidate['album artists'][0], track.get('album artist'))**1.2
    similarity *= straightCompare(candidate['artists'][0], track.get('artist'))**1.1
    return similarity

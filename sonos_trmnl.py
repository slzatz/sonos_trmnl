#!/home/slzatz/sonos_trmnl/bin/python

'''
Sends sonos information to trmnl devices plus images and lyrics"
'''
import time
import datetime
import random
import sys
import wikipedia
from bs4 import BeautifulSoup
import requests
from config import speaker 
from get_lyrics import get_lyrics
from soco.discovery import by_name

# cache for image urls - ? should actually cache the images
artists = {}

WIKI_REQUEST = "https://commons.wikimedia.org/w/index.php?search={search_term}&title=Special:MediaSearch&go=Go&type=image&uselang=en"
WIKI_FILE = "https://commons.wikimedia.org/wiki/File:" #Bob_Dylan_portrait.jpg
NUM_IMAGES = 8

def get_wiki_images(search_term):
    search_term = search_term.lower()
    search_term = search_term.replace(' ', '+')
    try:
        response  = requests.get(WIKI_REQUEST.format(search_term=search_term))
    except Exception as e:
        print(e)
        return []

    html = BeautifulSoup(response.text, 'html.parser')

    #div = html.find('div', class_="wbmi-media-search-results__list wbmi-media-search-results__list--image")
    # this change noted on 06/21/2021
    div = html.find('div', class_="sdms-search-results__list sdms-search-results__list--image")
    zz = div.find_all('a')
    zz = random.sample(zz, NUM_IMAGES if len(zz) >= NUM_IMAGES else len(zz))
    uris = []
    for link in zz:
        try:
            response = requests.get(link.get('href'))
        except Exception as e:
            print(e)
            continue
        html = BeautifulSoup(response.text, 'html.parser')
        div = html.find('div', class_="fullImageLink")
        img = div.a.get('href')
        uris.append(img)

    return uris

def filter_wiki_images(artist, uris):
    a = artist.lower().replace(" ", "_")
    b = artist.lower().replace(" ", "")
    filtered_uris = []
    for uri in uris:
        # match on artist name
        if a in uri.lower(): # sometimes name has a hyphen (like Drive-by Truckers)
            filtered_uris.append(uri) 
        elif a in uri.lower().replace("-", "_"):
            filtered_uris.append(uri) 
        # match on artist name with no spaces (seems rare)
        elif b in uri.lower():
            filtered_uris.append(uri) 
        else:
            # match if description has artist name
            zz = uri.split("/")[-1]
            xx = WIKI_FILE+zz
            response = requests.get(xx)
            html = BeautifulSoup(response.text, 'html.parser')
            td = html.find('td', class_="description")
            if td:
                if artist.lower() in td.get_text().lower().replace("_", " ").replace("-", " ")[:50]:
                    filtered_uris.append(uri) 
    return filtered_uris

if __name__ == "__main__":

    num_transport_errors = 0
    num_track_errors = 0

    master = by_name(speaker)

    try:
        master = by_name(speaker)
    except ValueError:
        print("Could not set master speaker by name")
        sys.exit(1)

    prev_title = ""
    prev_artist = ""
    lyrics = ""
    line_num = prev_line_num = 0
    rows = []
    all_rows = []

    while 1:
        try:
            state = master.get_current_transport_info()['current_transport_state']
        except Exception as e:
            print(f"Encountered error in state = master.get_current_transport_info(): {e}")
            state = 'ERROR'
            num_transport_errors += 1
            if num_transport_errors < 3:
                time.sleep(1)
                continue
            else:
                sys.exit(1)

        if state == 'PLAYING':

            try:
                track = master.get_current_track_info()
            except Exception as e:
                print(f"Encountered error in track = master.get_current_track_info(): {e}")
                num_track_errors += 1
                if num_track_errors < 3:
                    time.sleep(1)
                    continue
                else:
                    sys.exit(1)

            title = track.get('title', '')
            artist = track.get('artist', '')
            
            if prev_title != title or prev_artist != artist:
                prev_title = title
                prev_artist = artist
                duration = track.get('duration', 0)
                lyrics = get_lyrics(artist, title)
                if not lyrics:
                    lyrics = f"Couldn't retrieve lyrics for:\n{title} by {artist}"

                zz = []
                prev_line = None
                for line in lyrics.split("\n"):
                    if not(prev_line == "" and line == ""):
                        zz.append(line)
                        prev_line = line
                line_count = len(zz) 

                if not artist:
                    rows = all_rows = []
                    time.sleep(5)
                    continue

                else:
                    all_images = get_wiki_images(artist)
                    #print(all_rows)
                    likely_images = filter_wiki_images(artist, all_rows)
                    #print("all_rows", all_rows, "all_rows")

                
                print(f"Title: {title}, Artist: {artist}, Duration: {duration}, Lyrics lines: {line_count}, Images found: {len(all_images)}")
            time.sleep(.01) 


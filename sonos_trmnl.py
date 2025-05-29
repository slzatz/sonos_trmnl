#!/home/slzatz/sonos_trmnl/bin/python

'''
Sends sonos information to trmnl devices plus images and lyrics"
'''
import time
import sys
import requests
from config import speaker, server_url, access_token 
from get_lyrics import get_lyrics
from soco.discovery import by_name

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

        if state != 'PLAYING':
            time.sleep(1) 
            continue

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

            lyric_lines = []
            prev_line = None
            for line in lyrics.split("\n"):
                if not(prev_line == "" and line == ""):
                    lyric_lines.append(line)
                    prev_line = line
            line_count = len(lyric_lines) 

            # Generate HTML for e-ink display
            from string import Template
            with open('/home/slzatz/sonos_trmnl/template.html', 'r') as f:
                html_template = Template(f.read())
            
            # Limit lyrics to fit 800x480 display (approximately 15-20 lines)
            lyrics_lines = lyric_lines[:20] if len(lyric_lines) > 20 else lyric_lines
            display_lyrics = '\n'.join(lyrics_lines)
            
            # Populate template with current track info
            html_content = html_template.substitute(
                artist=artist or "Unknown Artist",
                title=title or "Unknown Title", 
                lyrics=display_lyrics
            )
            
            # Send to e-ink display API
            api_url = server_url+"/api/screens"
            headers = {
                    'Access-Token': access_token,
                    'Content-Type': 'application/json'
            }
            payload = {
                "image": {
                    "content": html_content,
                    "file_name": "sonos_display.png"
                }
            }
            
            try:
                response = requests.post(api_url, headers=headers, json=payload, verify=False)
                print(f"API Response: {response.status_code}")
                if response.status_code != 200:
                    print(f"Error: {response.text}")
            except Exception as e:
                print(f"Failed to send to display: {e}")
            
            print(f"Title: {title}, Artist: {artist}, Duration: {duration}, Lyrics lines: {line_count}")

        time.sleep(.01) 


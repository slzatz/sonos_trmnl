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
            
            # Dynamic font sizing based on lyric count
            SCREEN_HEIGHT = 480  # Total screen height in pixels
            BODY_PADDING = 12    # Top + bottom padding (6px each)
            HEADER_HEIGHT = 28   # Approximate header space (font + padding + border + margin)
            BASE_LYRICS_FONT_SIZE = 13  # Baseline font size in pixels
            LYRICS_LINE_HEIGHT = 1.3  # Line height multiplier
            COLUMN_COUNT = 2     # Number of columns for lyrics
            MIN_FONT_SIZE = 11   # Minimum readable font size
            MAX_FONT_SIZE = 18   # Maximum font size before it looks too large
            
            available_height = SCREEN_HEIGHT - BODY_PADDING - HEADER_HEIGHT
            actual_lyric_count = len(lyric_lines)
            
            # Calculate optimal font size based on actual lyric count
            if actual_lyric_count > 0:
                # Calculate what font size would best fill the available space
                target_pixels_per_line = available_height / (actual_lyric_count / COLUMN_COUNT)
                optimal_font_size = int(target_pixels_per_line / LYRICS_LINE_HEIGHT)
                
                # Constrain font size within reasonable bounds
                lyrics_font_size = max(MIN_FONT_SIZE, min(MAX_FONT_SIZE, optimal_font_size))
                
                # If we're at max font size, recalculate how many lines we can actually display
                pixels_per_line = lyrics_font_size * LYRICS_LINE_HEIGHT
                lines_per_column = int(available_height / pixels_per_line)
                max_lyrics_lines = lines_per_column * COLUMN_COUNT
                
                # Use either all lyrics or maximum displayable lines
                lyrics_lines = lyric_lines[:max_lyrics_lines] if len(lyric_lines) > max_lyrics_lines else lyric_lines
            else:
                lyrics_font_size = BASE_LYRICS_FONT_SIZE
                lyrics_lines = lyric_lines
            
            display_lyrics = '\n'.join(lyrics_lines)
            
            # Update template with dynamic font size
            template_content = html_template.template
            template_content = template_content.replace('font-size:13px', f'font-size:{lyrics_font_size}px')
            updated_template = Template(template_content)
            
            # Populate template with current track info
            html_content = updated_template.substitute(
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


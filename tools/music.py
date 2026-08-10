import webbrowser
import musicLibrary


def play_music(song):
    song = song.lower().strip()

    if song not in musicLibrary.music:
        return f"I couldn't find {song} in your music library."

    webbrowser.open(musicLibrary.music[song])

    return f"Playing {song}."
import webbrowser


WEBSITES = {
    "google": "https://google.com",
    "youtube": "https://youtube.com",
    "facebook": "https://facebook.com",
    "linkedin": "https://linkedin.com",
    "github": "https://github.com",
}


def open_website(name):
    name = name.lower().strip()

    if name not in WEBSITES:
        return f"I don't know the website {name}."

    webbrowser.open(WEBSITES[name])

    return f"Opening {name}."
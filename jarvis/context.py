import json
import os
import logging

from jarvis.config import CONTEXT_FILE
from jarvis.logging_config import setup_logging


logger = setup_logging()


# ==========================================
# DEFAULT CONTEXT
# ==========================================

DEFAULT_CONTEXT = {
    "last_city": None,
    "last_topic": None,
    "last_song": None,
    "last_website": None,
    "last_command": None,
    "last_tool": None,
    "last_response": None
}


# ==========================================
# LOAD CONTEXT
# ==========================================

def load_context():

    if not os.path.exists(
        CONTEXT_FILE
    ):

        return DEFAULT_CONTEXT.copy()


    try:

        with open(
            CONTEXT_FILE,
            "r",
            encoding="utf-8"
        ) as file:

            data = json.load(
                file
            )


        context = DEFAULT_CONTEXT.copy()

        context.update(
            data
        )

        return context


    except Exception as e:

        logger.exception(
            "Context load error"
       )

        return DEFAULT_CONTEXT.copy()


# ==========================================
# SAVE CONTEXT
# ==========================================

def save_context(context):

    try:

        with open(
            CONTEXT_FILE,
            "w",
            encoding="utf-8"
        ) as file:

            json.dump(
                context,
                file,
                indent=4,
                ensure_ascii=False
            )


    except Exception as e:

        logger.exception(
           "Context save error"
        )


# ==========================================
# UPDATE CONTEXT
# ==========================================

def update_context(
    command=None,
    tool=None,
    arguments=None,
    response=None
):

    context = load_context()


    if command:

        context[
            "last_command"
        ] = command


    if tool:

        context[
            "last_tool"
        ] = tool


    if response:

        context[
            "last_response"
        ] = response


    arguments = arguments or {}


    # --------------------------------------
    # City
    # --------------------------------------

    city = arguments.get(
        "city"
    )

    if city:

        context[
            "last_city"
        ] = city


    # --------------------------------------
    # Song
    # --------------------------------------

    song = arguments.get(
        "song"
    )

    if song:

        context[
            "last_song"
        ] = song


    # --------------------------------------
    # Website
    # --------------------------------------

    website = arguments.get(
        "name"
    )

    if website:

        context[
            "last_website"
        ] = website


    # --------------------------------------
    # Topic
    # --------------------------------------

    if tool == "get_weather":

        context[
            "last_topic"
        ] = "weather"


    elif tool == "get_news":

        context[
            "last_topic"
        ] = "news"


    elif tool == "play_music":

        context[
            "last_topic"
        ] = "music"


    elif tool == "open_website":

        context[
            "last_topic"
        ] = "website"


    save_context(
        context
    )


    return context


# ==========================================
# CLEAR CONTEXT
# ==========================================

def clear_context():

    save_context(
        DEFAULT_CONTEXT.copy()
    )


# ==========================================
# GET CONTEXT
# ==========================================

def get_context():

    return load_context()
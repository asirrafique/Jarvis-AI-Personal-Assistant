import logging
import requests

from jarvis.config import (
    NEWS_API_KEY,
    HTTP_TIMEOUT,
)
from jarvis.logging_config import setup_logging


logger = setup_logging()


# ==========================================
# GET NEWS
# ==========================================

def get_news():

    api_key = NEWS_API_KEY


    # --------------------------------------
    # Check API key
    # --------------------------------------

    if not api_key:

        return "News API key is missing."


    # --------------------------------------
    # NewsAPI endpoint
    # --------------------------------------

    url = (
        "https://newsapi.org/v2/everything"
    )


    params = {

        "q": "India",

        "language": "en",

        "sortBy": "publishedAt",

        "pageSize": 5,

        "apiKey": api_key

    }


    try:

        # ----------------------------------
        # Make request
        # ----------------------------------

        response = requests.get(
            url,
            params=params,
            timeout=HTTP_TIMEOUT
        )


        # ----------------------------------
        # Parse response
        # ----------------------------------

        data = response.json()


        # ----------------------------------
        # Check NewsAPI status
        # ----------------------------------

        if data.get(
            "status"
        ) != "ok":

            print(
                "NewsAPI Error:",
                data.get("message")
            )

            return (
                "Sorry, I could not fetch "
                "the news."
            )


        # ----------------------------------
        # Get articles
        # ----------------------------------

        articles = data.get(
            "articles",
            []
        )


        if not articles:

            return (
                "I could not find any news "
                "right now."
            )


        # ----------------------------------
        # Build headlines
        # ----------------------------------

        headlines = []


        for article in articles:

            title = article.get(
                "title"
            )

            source = article.get(
                "source",
                {}
            ).get(
                "name"
            )


            # Skip invalid Google News entries
            if not title:

                continue


            if title == "Google News":

                continue


            headlines.append(
                {
                    "title": title,
                    "source": source or "Unknown"
                }
            )


            if len(headlines) >= 5:

                break


        # ----------------------------------
        # No usable headlines
        # ----------------------------------

        if not headlines:

            return (
                "I could not find any news "
                "right now."
            )


        # ----------------------------------
        # Return structured data
        # ----------------------------------
        #
        # IMPORTANT:
        # The agent should receive data,
        # not spoken text.
        #

        return {
            "success": True,
            "articles": headlines
        }


    # ======================================
    # REQUEST ERROR
    # ======================================

    except requests.RequestException as e:

        print(
            "News Error:",
            e
        )

        return {
            "success": False,
            "error": (
                "Could not connect "
                "to the news service."
            )
        }


    # ======================================
    # GENERAL ERROR
    # ======================================

    except Exception as e:

        print(
            "News Error:",
            e
        )

        return {
            "success": False,
            "error": (
                "Something went wrong "
                "while fetching the news."
            )
        }
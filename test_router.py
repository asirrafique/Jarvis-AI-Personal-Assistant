from jarvis.router import ai_route


tests = [

    "What's the weather in Delhi?",

    "What about tomorrow?",

    "What about the day after tomorrow?",

    "What's the weather in Kolkata?",

    "What about tomorrow?",

    "Check the weather in Mumbai and tell me the latest news",

    "Open YouTube",

    "Play Believer",

    "What time is it?",

    "Explain artificial intelligence"
]


for command in tests:

    print("\n================================")
    print("User:", command)

    result = ai_route(command)

    print("Result:", result)
from jarvis.agent import run_agent


commands = [

    "What time is it?",

    "Open YouTube",

    "Play Believer",

    "Tell me the latest news",

    "What's the weather in Delhi?",

    "Check the weather in Delhi and tell me the latest news"

]


for command in commands:

    print(
        "\n================================"
    )

    print(
        "USER:",
        command
    )


    response = run_agent(
        command
    )


    print(
        "JARVIS:",
        response
    )
from jarvis.agent import run_agent


print(
    "\n================================"
)

print(
    "TEST 1"
)

response = run_agent(
    "What's the weather in Delhi?"
)

print(
    "Jarvis:",
    response
)


print(
    "\n================================"
)

print(
    "TEST 2"
)

response = run_agent(
    "What about tomorrow?"
)

print(
    "Jarvis:",
    response
)


print(
    "\n================================"
)

print(
    "TEST 3"
)

response = run_agent(
    "And what is the latest news?"
)

print(
    "Jarvis:",
    response
)
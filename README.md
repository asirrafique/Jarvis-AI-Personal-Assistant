# 🤖 Jarvis — Local AI Personal Assistant

> **A voice-enabled, local AI personal assistant powered by Ollama and Llama 3.2, featuring tool calling, long-term memory, context resolution, system automation, and a reliability-focused agent architecture.**

Jarvis is a Python-based personal AI assistant designed to interact with users through natural language and voice commands.

Instead of acting as a simple chatbot, Jarvis uses an **agent architecture** that interprets user requests, resolves context, retrieves relevant memory, creates structured tool plans, validates those plans, executes the required tools, and generates a final response.

The system runs locally using **Ollama + Llama 3.2**, keeping the core AI reasoning local on the user's machine.

---

## ✨ Features

### 🧠 Local AI Agent

* Powered by **Ollama**
* Uses **Llama 3.2** for local reasoning
* Structured JSON-based tool planning
* Tool selection based on user intent
* Fail-closed planning when the model produces invalid output
* Prevents unnecessary tool execution

### 🎙️ Voice Interaction

Jarvis supports voice-based interaction through speech recognition.

```text
Voice Input
     ↓
Speech Recognition
     ↓
Jarvis Agent
     ↓
Tool Planning
     ↓
Tool Execution
     ↓
Response
```

### 🧩 Context Resolution

Jarvis can understand follow-up requests that depend on previous commands.

For example:

```text
User: What is the weather in Delhi?

Jarvis: Today's weather...

User: What about tomorrow?

Jarvis: Tomorrow's weather in Delhi...
```

The context resolver converts the follow-up request into a complete command before it reaches the planning layer.

### 🧠 Long-Term Memory

Jarvis includes a persistent memory system that allows it to retrieve relevant information from previous interactions.

Example:

```text
User:
What programming language do I prefer?

Jarvis:
Your preferred programming language is Python.
```

Memory retrieval is handled separately from tool execution, allowing personal-memory questions to be answered without unnecessary tools.

### 🛠️ Tool Calling

Jarvis can dynamically select and execute tools depending on the user's request.

Current capabilities include:

| Tool           | Capability           |
| -------------- | -------------------- |
| `get_weather`  | Weather information  |
| `get_news`     | Latest news          |
| `get_time`     | Current time         |
| `get_date`     | Current date         |
| `play_music`   | Play music           |
| `open_website` | Open websites        |
| `open_app`     | Open applications    |
| `open_folder`  | Open folders         |
| `open_file`    | Open files           |
| `search_web`   | Web search interface |
| `open_url`     | Open explicit URLs   |

### 🖥️ System Automation

Jarvis can interact with the local Windows environment through controlled system tools.

Examples:

```text
Open Chrome
```

```text
Open my Downloads folder
```

```text
Open my project folder
```

```text
Open this file
```

Tool arguments are validated before execution to prevent unexpected parameters from being passed to system tools.

### 🌦️ Weather Intelligence

Jarvis understands natural date expressions such as:

```text
What is the weather in Delhi?
```

```text
What is the weather in Delhi tomorrow?
```

```text
What is the weather in Delhi the day after tomorrow?
```

Internally:

```text
today               → days = 0
tomorrow            → days = 1
day after tomorrow  → days = 2
```

### 🌐 Web & URL Tools

Jarvis supports explicit URL opening:

```text
Open https://github.com
```

It also has a `search_web` tool interface for web searches.

> **Note:** The search tool currently depends on external search providers and may require additional provider configuration depending on the network environment.

### 🛡️ Reliability & Error Handling

Jarvis is designed to fail safely instead of crashing when something goes wrong.

The agent handles:

* Invalid plans
* Invalid plan steps
* Unknown tools
* Unknown tool arguments
* Tool exceptions
* Tool failures
* Planner exceptions
* Response-generation exceptions
* Duplicate tool calls
* Invalid model output

A failed tool does not automatically prevent subsequent tools from executing.

---

# 🏗️ Architecture

```text
                         ┌────────────────────┐
                         │       User         │
                         └─────────┬──────────┘
                                   │
                                   ▼
                         ┌────────────────────┐
                         │ Voice / Text Input │
                         └─────────┬──────────┘
                                   │
                                   ▼
                         ┌────────────────────┐
                         │ Context Resolver   │
                         └─────────┬──────────┘
                                   │
                                   ▼
                         ┌────────────────────┐
                         │ Memory Retrieval   │
                         └─────────┬──────────┘
                                   │
                                   ▼
                         ┌────────────────────┐
                         │  Llama 3.2 /       │
                         │  Ollama Planner    │
                         └─────────┬──────────┘
                                   │
                                   ▼
                         ┌────────────────────┐
                         │ Plan Validation    │
                         └─────────┬──────────┘
                                   │
                                   ▼
                         ┌────────────────────┐
                         │  Tool Registry     │
                         └─────────┬──────────┘
                                   │
                 ┌─────────────────┼─────────────────┐
                 ▼                 ▼                 ▼
          ┌────────────┐    ┌────────────┐    ┌────────────┐
          │   System   │    │   Weather  │    │    Web     │
          │   Tools    │    │   & News   │    │   Tools    │
          └────────────┘    └────────────┘    └────────────┘
                 │                 │                 │
                 └─────────────────┼─────────────────┘
                                   ▼
                         ┌────────────────────┐
                         │ Tool Results       │
                         └─────────┬──────────┘
                                   │
                                   ▼
                         ┌────────────────────┐
                         │ Final Response     │
                         └─────────┬──────────┘
                                   │
                                   ▼
                                User
```

---

# 📁 Project Structure

```text
Jarvis-AI-Personal-Assistant/
│
├── jarvis/
│   ├── agent.py
│   ├── config.py
│   ├── context.py
│   ├── context_resolver.py
│   ├── conversation.py
│   ├── logging_config.py
│   ├── memory.py
│   ├── memory_context.py
│   ├── response.py
│   ├── router.py
│   ├── system_tools.py
│   └── tool_registry.py
│
├── tools/
│   ├── browser.py
│   ├── music.py
│   ├── news.py
│   ├── weather.py
│   └── web.py
│
├── tests/
│   ├── test_config.py
│   ├── test_phase5_reliability.py
│   ├── test_planner.py
│   ├── test_tools.py
│   └── test_web.py
│
├── data/
├── logs/
│
├── main.py
├── run_jarvis.py
├── client.py
├── musicLibrary.py
├── requirements.txt
├── .env.example
└── .gitignore
```

---

# ⚙️ Tech Stack

### AI / GenAI

* Python
* Ollama
* Llama 3.2
* Local LLM inference
* Agent / tool-calling architecture
* Prompt-based structured planning

### Backend / Application

* Python
* Requests
* Python-dotenv
* JSON
* Logging
* Modular tool registry

### Voice

* Speech recognition
* Pygame
* Windows audio integration

### Testing

* Pytest
* Automated reliability tests
* Tool validation tests
* Planner tests
* Configuration tests
* Web-tool tests

---

# 🚀 Getting Started

## 1. Clone the repository

```bash
git clone https://github.com/asirrafique/Jarvis-AI-Personal-Assistant.git
cd Jarvis-AI-Personal-Assistant
```

## 2. Create a virtual environment

### Windows

```powershell
python -m venv .venv
```

Activate it:

```powershell
.\.venv\Scripts\Activate.ps1
```

## 3. Install dependencies

```powershell
python -m pip install -r requirements.txt
```

## 4. Install Ollama

Install Ollama and make sure it is running locally.

Then pull the required models:

```powershell
ollama pull llama3.2
```

For memory embeddings:

```powershell
ollama pull nomic-embed-text
```

Verify:

```powershell
ollama list
```

You should see the required models.

## 5. Configure environment variables

Create a `.env` file:

```env
NEWS_API_KEY=your_news_api_key_here
```

Never commit `.env` to GitHub.

The repository includes `.env.example` as a safe configuration template.

---

# ▶️ Running Jarvis

## Text / Agent Mode

```powershell
python run_jarvis.py
```

You can then interact with Jarvis:

```text
You: What is the weather in Delhi?

Jarvis: Today's weather in Delhi...
```

Other examples:

```text
You: What about tomorrow?
```

```text
You: What programming language do I prefer?
```

```text
You: Open my Downloads folder.
```

```text
You: Open https://github.com
```

## Voice Mode

```powershell
python main.py
```

Jarvis will initialize the voice interaction system and listen for commands.

---

# 🧪 Running Tests

Run the complete test suite:

```powershell
python -m pytest -v
```

The project includes tests covering:

* Configuration
* Tool registry
* Tool validation
* Tool execution
* Weather
* Time
* Date
* Music
* YouTube
* Memory questions
* Context-aware commands
* System automation
* Web tools
* Reliability and failure handling

Example:

```text
52 tests
```

The test suite is designed to ensure that new agent capabilities do not break existing functionality.

---

# 🔐 Security

Sensitive configuration should be stored in `.env`.

Never commit:

```text
.env
```

Local runtime data and generated files are also excluded through `.gitignore`.

For production deployments, API keys should be provided through secure environment-variable or secret-management systems.

---

# 💡 Example Commands

### Weather

```text
What is the weather in Delhi?
```

```text
What about tomorrow?
```

```text
And the day after tomorrow?
```

### Memory

```text
What programming language do I prefer?
```

### System

```text
Open my Downloads folder.
```

```text
Open my project folder.
```

### Web

```text
Search the web for React tutorials.
```

```text
Open https://github.com
```

### Music

```text
Play music.
```

```text
Open YouTube and play music.
```

---

# 📊 Reliability

Jarvis uses a defensive execution architecture:

```text
LLM Output
    ↓
JSON Parsing
    ↓
Plan Normalization
    ↓
Plan Validation
    ↓
Tool Validation
    ↓
Safe Execution
    ↓
Result Handling
    ↓
Final Response
```

If any stage fails, Jarvis attempts to fail gracefully rather than terminating the entire application.

---

# 🎯 Project Goals

Jarvis was built to explore practical AI-agent engineering concepts including:

* Local LLMs
* Tool calling
* Agent planning
* Context management
* Long-term memory
* Voice interaction
* System automation
* Structured model output
* Defensive programming
* Automated testing

The goal is to build an AI assistant that is **modular, extensible, locally runnable, and reliable**.

---

# 🔮 Future Improvements

Potential future improvements include:

* More reliable search-provider integration
* Browser automation
* Calendar integration
* Email integration
* More advanced voice interaction
* Wake-word detection
* Streaming responses
* Improved memory management
* GUI interface
* More system automation
* Additional local AI models

---

# 👨‍💻 Author

**Asir Rafique**

Computer Science & Engineering | Full-Stack Developer | AI & GenAI Developer

### Connect with me

* GitHub: https://github.com/asirrafique
* LinkedIn: https://www.linkedin.com/in/asir-rafique07
* Portfolio: https://portfolio-asir3.vercel.app/

---

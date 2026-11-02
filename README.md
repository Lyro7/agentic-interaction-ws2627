# Agentic Human-AI Interaction

Exercise 1: First Tool Call — Ulm University, Winter Semester 2026/27.

A simple LLM-based agent that retrieves calendar events using tool calling.

## Setup

Requires Python 3.11 or newer.

1. Create and activate a virtual environment:

   ```bash
   python3 -m venv .venv
   source .venv/bin/activate
   ```

2. Install dependencies:

   ```bash
   pip install -r requirements.txt
   ```

3. Create a `.env` file in the project root:

   ```env
   OPENAI_BASE_URL=https://api.groq.com/openai/v1
   MODEL=openai/gpt-oss-20b
   OPENAI_API_KEY=your_api_key
   DATA_BASE_URL=https://jhbelz.github.io/agentic-interaction-data/v1
   ```

## Usage

Run from the repository root:

```bash
python -m agent "Was steht am 29.10.2026 im Kalender?"
```

## How it works

The LLM requests the `getCalendar` tool, which retrieves calendar data via HTTP. The results are returned to the LLM to generate an answer.

Each run creates a JSONL log file in `logs/`.

Environment variables take precedence over `.env`.
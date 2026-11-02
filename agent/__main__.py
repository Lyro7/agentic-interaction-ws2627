import os
import sys
import json
import uuid
import time
import requests

from pathlib import Path
from datetime import datetime, timezone
from dotenv import load_dotenv
from openai import OpenAI

# Tool description for the LLM
tools = [
    {
        "type": "function",
        "function": {
            "name": "getCalendar",
            "description": "Get calendar events for a given date.",
            "parameters": {
                "type": "object",
                "properties": {
                    "date": {
                        "type": "string",
                        "description": "Calendar date in YYYY-MM-DD format."
                    }
                },
                "required": ["date"]
            }
        }
    }
]

# Actual tool implementation
def getCalendar(date: str):
    base_url = os.environ["DATA_BASE_URL"].rstrip("/")
    url = f"{base_url}/calendar/{date}.json"

    response = requests.get(url, timeout=10)

    if response.status_code == 404:
        return {"message": f"No calendar data available for {date}."}

    response.raise_for_status()

    return response.json()

# JSONL logging
def writeLog(log_file, run_id, event, model, ok=True,
             tool=None, args=None, duration_ms=0, **extra):

    entry = {
        "ts": datetime.now(timezone.utc).isoformat(),
        "run_id": run_id,
        "event": event,
        "tool": tool,
        "args": args,
        "ok": ok,
        "model": model,
        "duration_ms": round(duration_ms, 2),
        **extra
    }

    with open(log_file, "a", encoding="utf-8") as file:
        file.write(json.dumps(entry, ensure_ascii=False) + "\n")

def main():
    question = " ".join(sys.argv[1:])

    # Load the .env file and make the environment variables accessible
    load_dotenv(Path(__file__).resolve().parent.parent / ".env", override=False)
    
    model = None

    # Create one log file per run
    run_id = str(uuid.uuid4())

    log_dir = Path(__file__).resolve().parent.parent / "logs"
    log_dir.mkdir(parents=True, exist_ok=True)

    log_file = log_dir / f"{run_id}.jsonl"
    run_start = time.perf_counter()

    try:
        model = os.environ["MODEL"]

        writeLog(
        log_file, run_id, "user_task", model,
        args={"question": question}
        )

        if not question.strip():
            raise ValueError("No question provided.")

        client = OpenAI(
            api_key=os.environ["OPENAI_API_KEY"],
            base_url=os.environ["OPENAI_BASE_URL"]
        )

        messages = [
            {
                "role": "system",
                "content": (
                    "You are a calendar assistant. "
                    "Use getCalendar to answer questions about calendar appointments. "
                    "Only report appointments returned by the tool. "
                    "If no data is available, explain that clearly."
                )
            },
            {"role": "user", "content": question}
        ]

        # First model call
        response = client.chat.completions.create(
            model=model,
            messages=messages,
            tools=tools,
            tool_choice="required"
        )

        message = response.choices[0].message
        messages.append(message)

        if not message.tool_calls:
            raise RuntimeError("Model did not request a tool.")

        # Execute requested tools
        for call in message.tool_calls:
            args = json.loads(call.function.arguments)

            writeLog(
                log_file, run_id, "tool_call", model,
                tool=call.function.name,
                args=args
            )

            tool_start = time.perf_counter()

            try:
                if call.function.name != "getCalendar":
                    raise ValueError(f"Unknown tool: {call.function.name}")

                result = getCalendar(args["date"])

                writeLog(
                    log_file, run_id, "tool_result", model,
                    tool=call.function.name,
                    args=args,
                    duration_ms=(
                        time.perf_counter() - tool_start
                    ) * 1000,
                    result=result
                )

            except Exception as error:
                writeLog(
                    log_file, run_id, "tool_result", model,
                    ok=False,
                    tool=call.function.name,
                    args=args,
                    duration_ms=(
                        time.perf_counter() - tool_start
                    ) * 1000,
                    error=str(error)
                )
                raise

            messages.append({
                "role": "tool",
                "tool_call_id": call.id,
                "content": json.dumps(result, ensure_ascii=False)
            })

        # Second model call
        response = client.chat.completions.create(
            model=model,
            messages=messages
        )

        answer = response.choices[0].message.content

        if answer is None:
            raise RuntimeError("Model returned no final answer.")

        writeLog(
            log_file, run_id, "final", model,
            duration_ms=(
                time.perf_counter() - run_start
            ) * 1000,
            answer=answer
        )

        print(answer)

    except Exception as error:
        writeLog(
            log_file, run_id, "error", model,
            ok=False,
            duration_ms=(
                time.perf_counter() - run_start
            ) * 1000,
            error=str(error)
        )

        print(f"Error: {error}", file=sys.stderr)
        sys.exit(1)

if __name__ == "__main__":
    main()

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

MAX_STEPS = 5

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

def getCalendar(date: str):
    base_url = os.environ["DATA_BASE_URL"].rstrip("/")
    url = f"{base_url}/calendar/{date}.json"

    response = requests.get(url, timeout=10)

    if response.status_code == 404:
        return {"message": f"No calendar data available for {date}."}

    response.raise_for_status()

    return response.json()

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

    load_dotenv(Path(__file__).resolve().parent.parent / ".env", override=False)
    
    model = None

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
            api_key =os.environ["OPENAI_API_KEY"],
            base_url=os.environ["OPENAI_BASE_URL"]
        )

        messages = [
            {
                "role": "system",
                "content": (
                    "You are a calendar assistant. "
                    "Call getCalendar for every date requested before giving a final answer. "
                    "If a lookup fails, report the failure for that date and continue "
                    "with all remaining dates. "
                    "Report the result for each date separately using only tool results. "
                    "Write the final answer in plain language, grouped by date. "
                    "For each event, list the time, title, and location if available. "
                    "If events is an empty list, say 'No events scheduled' for that date. "
                    "Only report a failed lookup if the tool result contains an error field. "
                    "Never output raw JSON."
                )
            },
            {"role": "user", "content": question}
        ]
        
        for step in range(MAX_STEPS):

            response = client.chat.completions.create(
                model=model,
                messages=messages,
                tools=tools,
                tool_choice="auto"
            )

            message = response.choices[0].message
            messages.append(message)

            if not message.tool_calls:
                answer = message.content
                break
            
            for call in message.tool_calls:
                args = None
                tool_start = time.perf_counter()

                try:
                    args = json.loads(call.function.arguments)

                    writeLog(
                        log_file, run_id, "tool_call", model,
                        tool=call.function.name,
                        args=args
                    )

                    if call.function.name != "getCalendar":
                        raise ValueError(f"Unknown tool: {call.function.name}")

                    result = getCalendar(args["date"])

                except Exception as error:
                    result = {"error": str(error)}
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

                else:
                    writeLog(
                    log_file, run_id, "tool_result", model,
                    tool=call.function.name,
                    args=args,
                    duration_ms=(time.perf_counter() - tool_start) * 1000,
                    result=result,
                )
                    
                messages.append({
                    "role": "tool",
                    "tool_call_id": call.id,
                    "content": json.dumps(result, ensure_ascii=False)
                })

        else:
            raise RuntimeError("Step limit reached.")

        if not answer or not answer.strip():
            raise RuntimeError("Model returned no final answer")

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

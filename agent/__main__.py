import os
import sys
import json
import uuid
import time

from pathlib import Path
from datetime import datetime, timezone
from dotenv import load_dotenv
from openai import OpenAI

from .tools import tool_handlers, tools

MAX_STEPS = 5

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
                "You are an assistant for calendar events, weather, and train connections. "
                "Use getCalendar for every requested calendar date, getWeather for weather "
                "questions and umbrella recommendations, and getTransit for train journeys. "
                "For combined questions, call every relevant tool before answering. "

                "Use lowercase city slugs such as ulm and muenchen (Munich). "
                "If no train origin is stated or implied, assume Ulm and clearly state this. "
                "For travel weather, use the destination unless another place is specified. "

                "Base all factual claims and recommendations on tool results. "
                "Never invent missing values. If data is unavailable, say so explicitly. "
                "If a lookup fails, identify the affected lookup and continue with any "
                "remaining results. "

                "Group the final answer by date and write in plain language. "
                "For calendar events, include the time, title, and location when available. "
                "If the events list is empty, say 'No events scheduled' for that date. "
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

                    handler = tool_handlers.get(call.function.name)
                    if handler is None:
                        raise ValueError(f"Unknown tool: {call.function.name}")

                    result = handler(**args)

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

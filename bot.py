import argparse
import json
import os
import re
import subprocess
import sys
import time

from openai import OpenAI
from watchdog.events import FileSystemEventHandler
from watchdog.observers import Observer

DEFAULT_QUESTION = """Process the context according to the task description."""


def _clean_model_output(s: str) -> str:
    if s is None:
        return ""
    text = s
    # Remove any <think>...</think> blocks or stray tags
    try:
        text = re.sub(
            r"(<think>)?.*?</think>\s*", "", text, flags=re.DOTALL | re.IGNORECASE
        )
        text = re.sub(r"</?think>", "", text, flags=re.IGNORECASE)

    except Exception:
        pass
    text = text.strip()
    # Strip code fences if present
    if text.startswith("```"):
        # remove the first fence line
        lines = text.splitlines()
        # drop first line (``` or ```python)
        lines = lines[1:]
        # drop trailing fence if exists
        if lines and lines[-1].strip().startswith("```"):
            lines = lines[:-1]
        text = "\n".join(lines).strip()
    # Remove surrounding triple quotes if model returned them
    for q in ('"""', "'''"):
        if text.startswith(q) and text.endswith(q):
            text = text[len(q) : -len(q)].strip()
            break
    return text


class DistilLabsLLM(object):
    def __init__(self, model_name: str, api_key: str = "EMPTY", port: int = 11434):
        self.model_name = model_name
        self.client = OpenAI(base_url=f"http://127.0.0.1:{port}/v1", api_key=api_key)

    def get_prompt(
        self,
        question: str,
        context: str,
    ) -> list[dict[str, str]]:
        return [
            {
                "role": "system",
                "content": """
You are a problem solving model working on task_description XML block:
<task_description>## Task
Generate a concise git commit message from git diff output. The commit message must have a title under 60 characters followed by 2-4 sentences summarizing the higher-level changes. Focus on understanding the code changes in TypeScript/JavaScript codebases.

## Inputs
Short, meaningful git diff outputs generated with `git diff --no-ext-diff -U5` showing focused code changes. Each diff represents a single coherent change such as: adding error handling to a function, introducing a new utility function, enhancing component behavior, or modifying existing functionality with clear intent. The diffs are from TypeScript/JavaScript projects across various contexts (Serverless, React, Node.js, etc.) and include 5 lines of context around each change.

## Outputs
A JSON object with structure `{ "commit_message": COMMIT_MESSAGE }` where COMMIT_MESSAGE is a string containing a title (under 60 chars) followed by 2-4 summary sentences describing the changes at a higher level, focusing on the purpose and impact rather than implementation details.</task_description>
You will be given a single task with context in the context XML block and the task in the question XML block
Solve the task in question block based on the context in context block.
Generate only the answer, do not generate anything else
""",
            },
            {
                "role": "user",
                "content": f"""

Now for the real task, solve the task in question block based on the context in context block.
Generate only the solution, do not generate anything else
<context>{context}</context>
<question>{question}</question>
/no_think
""",
            },
        ]

    def invoke(self, question: str, context: str) -> str:
        chat_response = self.client.chat.completions.create(
            model=self.model_name,
            messages=self.get_prompt(question, context),
            temperature=0,
        )
        return _clean_model_output(chat_response.choices[0].message.content)


def run_git_diff_analysis(repository_path, client):
    """Run git diff and analyze the changes."""
    try:
        result = subprocess.run(
            [
                "git",
                "diff",
                "--no-ext-diff",
                "-U0",
                "HEAD",
            ],
            cwd=repository_path,
            capture_output=True,
            text=True,
            check=True,
        )

        context = result.stdout
        # Git adds function context to the diff, remove it
        context = "\n".join(
            re.sub(r"(@@[^@]*@@).*", r"\1", line) if line.startswith("@@") else line
            for line in context.split("\n")
        )
    except subprocess.CalledProcessError as e:
        print(f"Error running git diff: {e.stderr}", file=sys.stderr)
        return
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        return

    if not context:
        print("No changes found")
        return

    print("\n" + "=" * 60)
    print(f"Changes detected at {time.strftime('%Y-%m-%d %H:%M:%S')}")
    print()
    print("Generating commit message suggestion")
    print("=" * 60 + "\n")
    print()

    json_response_str = client.invoke(DEFAULT_QUESTION, context)
    json_response = json.loads(json_response_str)
    print(json_response["commit_message"])


class RepositoryChangeHandler(FileSystemEventHandler):
    """Handles file system events in the repository."""

    def __init__(self, repository_path, client, debounce_seconds=10):
        self.repository_path = repository_path
        self.client = client
        self.debounce_seconds = debounce_seconds
        self.last_trigger_time = 0

    def on_any_event(self, event):
        # Ignore .git directory changes and directory events
        if ".git" in event.src_path or event.is_directory:
            return

        current_time = time.time()
        if current_time - self.last_trigger_time >= self.debounce_seconds:
            self.last_trigger_time = current_time
            run_git_diff_analysis(self.repository_path, self.client)


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--api-key", type=str, default="EMPTY", required=False)
    parser.add_argument(
        "--model",
        type=str,
        default="distil-commit-bot-ts-Qwen3-0.6B",
        required=False,
    )
    parser.add_argument("--port", type=int, default=11434, required=False)
    parser.add_argument(
        "--repository",
        type=str,
        default=None,
        required=True,
        help="Path to the git repository you want to watch",
    )
    parser.add_argument(
        "--watch",
        action="store_true",
        help="Watch for file changes and run continuously",
    )
    args = parser.parse_args()

    repository_path = os.path.abspath(os.path.expanduser(args.repository))

    if not os.path.exists(repository_path):
        print(
            f"Error: Repository path does not exist: {repository_path}", file=sys.stderr
        )
        sys.exit(1)

    client = DistilLabsLLM(model_name=args.model, api_key=args.api_key, port=args.port)

    if args.watch:
        print(f"Watching repository: {repository_path}")
        print("Press Ctrl+C to stop...\n")

        event_handler = RepositoryChangeHandler(repository_path, client)
        observer = Observer()
        observer.schedule(event_handler, repository_path, recursive=True)
        observer.start()

        try:
            while True:
                time.sleep(1)
        except KeyboardInterrupt:
            observer.stop()
            print("\nStopped watching repository")
        observer.join()
    else:
        print("Try --watch to watch for file changes and run continuously")
        run_git_diff_analysis(repository_path, client)

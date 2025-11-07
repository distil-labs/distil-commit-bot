import argparse
import os
import re
import subprocess
import sys
import time

from openai import OpenAI
from watchdog.events import FileSystemEventHandler
from watchdog.observers import Observer

DEFAULT_QUESTION = """Process the context according to the task description."""


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
Generate a concise yet informative git commit message draft from a `git diff` output. The message should include a title (under 50 characters) and optionally a body for additional context when necessary. The commit message should summarize the changes by identifying what was added, modified, or removed, and explain the purpose or impact of those changes in a clear, technical manner.

## Inputs
The raw output string from the `git diff` command, which shows changes between commits, commit and working tree, etc. This includes file paths, added/removed lines, and change context across multiple files. The diff may include code modifications, new files, deleted files, and comments indicating the nature of changes.

## Outputs
A string in conventional git commit message format: a title line (<=50 characters) followed by an optional blank line and a body paragraph for elaboration. The body should provide specific details about the changes made, including functionality added, bugs fixed, or architectural improvements. Omit the body if the title sufficiently describes the changes.</task_description>
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
""",
            },
        ]

    def invoke(self, question: str, context: str) -> str:
        chat_response = self.client.chat.completions.create(
            model=self.model_name,
            messages=self.get_prompt(question, context),
            temperature=0,
        )
        return chat_response.choices[0].message.content


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
    print(client.invoke(DEFAULT_QUESTION, context))


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
        "--model", type=str, default="commit-bot-llama-1.0-1B", required=False
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

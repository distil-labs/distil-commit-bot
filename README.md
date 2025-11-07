# distil-commit-boy

We trained an SLM assistants for assistance with commit messages - Llama 3.2 model (1B parameters) that you can run *locally* via Ollama!

### 1. Installation
First, install [Ollama](https://ollama.com), following the instructions on their website.

Then set up the virtual environment:
```
python -m venv .venv
. .venv/bin/activate
pip install huggingface_hub openai watchdog
```

The model is hosted on huggingface:
- [distil-labs/Distil-commit-bot-1.0-1B](https://huggingface.co/distil-labs/Distil-commit-bot-1.0-1B)

Finally, download the models from huggingface and build them locally:
```
hf download distil-labs/Distil-commit-bot-1.0-1B --local-dir distil-model

cd distil-model
ollama create commit-bot-1.0 -f Modelfile
```

### 2. Run the assistant
The commit bot with diff the git repository provided via `--repository`
option and suggest a commit message. Use the `--watch` option to re-run
the assistant whenever the repository changes.

```
python bot.py --repository <absolute_or_relative_repository_path>

# optionally, --watch
python bot.py --repository <absolute_or_relative_repository_path> --watch
```

### 5. Fine-tuning setup

### FAQ
**Q: Why don't we just use Llama3.X yB for this??**

We focus on small models (< 8B parameters), and these make errors when used out of the box (see 5.)

**Q: I want to train a small language model for my use-case**

A: Visit our [website](https://www.distillabs.ai) and reach out to us, we offer custom solutions.

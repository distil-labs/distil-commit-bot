# distil-commit-bot TS

We trained an SLM assistant for help with commit messages on TypeScript codebases - Qwen 3 model (0.6B parameters) that you can run *locally*!

<p align="center">
  <img width="384" height="384" alt="Commit Bot" src="bot.png" />
</p>

### Installation
First, install [Ollama](https://ollama.com), following the instructions on their website.

Then set up the virtual environment:
```
python -m venv .venv
. .venv/bin/activate
pip install huggingface_hub openai watchdog
```

or using [uv](https://docs.astral.sh/uv/):
```
uv sync
```

The model is hosted on huggingface:
- [distil-labs/distil-commit-bot-ts-Qwen3-0.6B](https://huggingface.co/distil-labs/distil-commit-bot-ts-Qwen3-0.6B)

Finally, download the models from huggingface and build them locally:
```
hf download distil-labs/distil-commit-bot-ts-Qwen3-0.6B --local-dir distil-model

cd distil-model
ollama create distil-commit-bot-ts-Qwen3-0.6B -f Modelfile
```

### Run the assistant
The commit bot with diff the git repository provided via `--repository`
option and suggest a commit message. Use the `--watch` option to re-run
the assistant whenever the repository changes.

```
python bot.py --repository <absolute_or_relative_git_repository_path>
# or
uv run bot.py --repository <absolute_or_relative_git_repository_path>

# Watch for file changes in the repository path:
python bot.py --repository <absolute_or_relative_git_repository_path> --watch
# or
uv run bot.py --repository <absolute_or_relative_git_repository_path> --watch
```

### Examples

See [examples](/examples)

### Training & Evaluation
The tuned models were trained using knowledge distillation, leveraging the teacher model GPT-OSS-120B. The data+config+script used for finetuning can be found in [data](/data). We used 20 typescript git diff examples (created using [distillabs' vibe tuning](https://www.distillabs.ai/blog/vibe-tuning-the-art-of-fine-tuning-small-language-models-with-a-prompt)) as seed data and supplemented them with 10,000 synthetic examples across various typescript use cases (frontend, backend, react etc.).

We compare the teacher model and the student model on 10 held-out test examples using LLM-as-a-judge evaluation:

| Model              | Size | Accuracy |
|--------------------|------|----------|
| GPT-OSS (thinking) | 120B | 1.00     |
| Qwen3 0.6B (tuned) | 0.6B | 0.90     |
| Qwen3 0.6B (base)  | 0.6B | 0.60     |


Evaluation Criteria:
LLM-as-a-judge: The training config file and train/test data splits are available under [`/data`](/data).

### FAQ
**Q: Why don't we just use Llama3.X yB for this??**

We focus on small models (< 8B parameters), and these make errors when used out of the box (see 5.)

**Q: I want to train a small language model for my use-case**

A: Visit our [website](https://www.distillabs.ai) and reach out to us, we offer custom solutions.

  ---

## Links

<p align="center">
  <a href="https://www.distillabs.ai/?utm_source=github&utm_medium=referral&utm_campaign=distil-commit-bot">
    <img src="https://github.com/distil-labs/badges/blob/main/badge-distillabs-home.svg?raw=true" alt="Distil Labs Homepage" />
  </a>
  <a href="https://github.com/distil-labs">
    <img src="https://github.com/distil-labs/badges/blob/main/badge-github.svg?raw=true" alt="GitHub" />
  </a>
  <a href="https://huggingface.co/distil-labs">
    <img src="https://github.com/distil-labs/badges/blob/main/badge-huggingface.svg?raw=true" alt="Hugging Face" />
  </a>
  <a href="https://www.linkedin.com/company/distil-labs/">
    <img src="https://github.com/distil-labs/badges/blob/main/badge-linkedin.svg?raw=true" alt="LinkedIn" />
  </a>
  <a href="https://distil-labs-community.slack.com/join/shared_invite/zt-36zqj87le-i3quWUn2bjErRq22xoE58g">
    <img src="https://github.com/distil-labs/badges/blob/main/badge-slack.svg?raw=true" alt="Slack" />
  </a>
  <a href="https://x.com/distil_labs">
    <img src="https://github.com/distil-labs/badges/blob/main/badge-twitter.svg?raw=true" alt="Twitter" />
  </a>
</p>


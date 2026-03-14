# Weekly Review Automation

Automates a weekly personal review. It parses your diet and exercise exports,
pulls your monthly goals/tasks from TickTick, prompts you for short reflections,
and writes a formatted Markdown review to a configurable output directory (for
example, a folder in an Obsidian vault).

## What it does

- **Diet review**: parses a NetDiary (MyNetDiary) CSV/Excel export and computes
  nutrition stats for the week (days within calorie target, days hitting protein
  target, averages).
- **Exercise review**: parses a Hevy workout CSV export and summarizes sessions,
  durations, and workout days against a weekly target.
- **Goals review**: fetches tasks from a TickTick project and groups them by
  domain using title prefixes (e.g. `[Health]`, `[Career]`), splitting discrete
  tasks from recurring "process" goals.
- **Interactive prompts**: collects your progress on process goals and short
  per-domain reflections.
- **Markdown output**: assembles everything into a single weekly-review Markdown
  file named `Weekly review YYYY-MM-DD.md` in your configured folder.

## Quick start

### 1. Install dependencies

```bash
pip install -r requirements.txt
```

### 2. Configure

```bash
cp config.example.yaml config.yaml
```

Then edit `config.yaml` with your own settings (TickTick project id, goal
domains, targets, and output path). `config.yaml` is gitignored so your personal
values stay out of version control.

```yaml
ticktick:
  monthly_goals_project_id: "your_project_id_here"

paths:
  obsidian_vault: "/path/to/your/notes-vault"
  weekly_review_folder: "Goals/Weekly reviews"

targets:
  daily_calorie_max: 2000
  daily_protein_min: 100
  weekly_gym_sessions: 3
```

### 3. Set TickTick credentials (environment variables)

Credentials are never stored in the repo. Provide them via the environment:

```bash
export TICKTICK_USERNAME="your_email@example.com"
export TICKTICK_PASSWORD="your_password"
```

### 4. Export your data

- **Diet (NetDiary / MyNetDiary):** export your log as CSV or Excel.
- **Workouts (Hevy):** export your workouts as CSV.

### 5. Run

```bash
python weekly_review.py \
  --netdiary-csv ~/Downloads/netdiary_export.csv \
  --heavy-csv ~/Downloads/hevy_export.csv \
  --start-date 2026-01-05 \
  --end-date 2026-01-11 \
  --config config.yaml
```

The script will parse your data, fetch goals from TickTick, prompt for progress
and reflections, and write the review to your configured folder.

## Useful flags

- `--dry-run` — preview the generated review without writing a file.
- `--skip-ticktick` — skip the TickTick integration (useful for testing or if the
  API is unavailable); you can add goals to the review manually afterward.
- `--non-interactive` — skip the interactive prompts (pair with `--skip-ticktick`
  for a fully unattended run).

### Finding your TickTick project id

Open TickTick in a browser, navigate to your goals project, and read the id from
the URL: `https://ticktick.com/webapp/#/project/<PROJECT_ID>/tasks`.

## Try it with sample data

The `sample_data/` directory contains small **synthetic** diet and workout files
so you can see the parsers and Markdown generator work end to end without any
real personal data:

```bash
python demo_test.py
```

## Project structure

```
weekly-review-automation/
├── weekly_review.py          # Main script / orchestrator
├── diet_parser.py            # NetDiary diet parsing + nutrition stats
├── exercise_parser.py        # Hevy workout parsing + summaries
├── ticktick_client.py        # TickTick auth + task retrieval
├── markdown_generator.py     # Markdown assembly + interactive prompts
├── config.example.yaml       # Config template (copy to config.yaml)
├── requirements.txt          # Python dependencies
├── demo_test.py              # End-to-end demo using sample_data/
├── test_weekly_review.py     # Unit tests (pytest)
├── sample_data/              # Synthetic fixtures (diet + workouts)
└── README.md
```

## Tests

Unit tests cover the diet and exercise parsers, task grouping/classification, and
Markdown generation:

```bash
pytest test_weekly_review.py -v
```

## Notes

- The script only reads your source exports; it never modifies them.
- Keep `config.yaml` and `.ticktick_token.json` out of version control (both are
  already gitignored).

## License

Personal automation tool shared as a portfolio example. Feel free to adapt it.

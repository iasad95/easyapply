# LinkedIn Easy Apply (GPT Optional)

Automates LinkedIn Easy Apply workflows with browser automation and optional GPT-assisted form answers.

## Disclaimer

This project is for educational and research use only.

Using automation on LinkedIn may violate platform Terms of Service and may lead to account restrictions or suspension. Use at your own risk.

## What This Project Does

- Opens LinkedIn jobs and applies through Easy Apply flows
- Uses your local files in `Templates/` for resume/profile/filters
- Optionally uses OpenAI (`OPEN_AI_API_KEY`) to answer application questions
- Falls back to deterministic answers from `personalInfo` when no OpenAI key is configured

## Prerequisites

- Python 3.10+ (3.11 recommended)
- Google Chrome installed
- A LinkedIn account

## Setup

1) Create and activate a virtual environment:

```bash
python3 -m venv .venv
source .venv/bin/activate
```

1) Install dependencies:

```bash
pip install -r requirements.txt
```

1) Configure environment variables:

```bash
cp .env.example .env
```

Update `.env`:

- `LINKEDIN_EMAIL=...`
- `LINKEDIN_PASSWORD=...`
- `OPEN_AI_API_KEY=...` (optional, enables GPT answers)
- `SKIP_APPLY=False` (optional safety toggle)
- `DISABLE_DESCRIPTION_FILTER=False` (optional)

## Configure Template Files

The app expects a data folder (default usage is `./Templates`) with these files:

- `config.yaml` (required)
- `resume.pdf` (required, filename must include `resume`)
- `resume.md` or `plain_text_resume.md` (required)
- `profile.md` or `personal_data.md` (required)
- `filters.md` or `job_filters.md` or `job-filters.md` (required)
- `cover_letter.pdf` (optional)
- `cover_letter.md` or `plain_text_cover_letter.md` (optional)

You can start from the provided examples in `Templates/`.

## Run

```bash
python3 main.py ./Templates
```

Use another folder if you keep multiple profiles:

```bash
python3 main.py /path/to/your/data-folder
```

## How Answering Works

- If `OPEN_AI_API_KEY` is present, GPT-based answering is used.
- If not, the app uses rule-based answers from `personalInfo` in `config.yaml` and your markdown files.

## Output

Run artifacts are written to:

- `Templates/output/` (or `<your-data-folder>/output/`)

## Common Issues

- **Chrome fails to start**
  - Install Google Chrome and retry.
  - Ensure dependencies were installed in the active virtual environment.
  - Optionally set `CHROMEDRIVER_PATH` in `.env` if you use a custom driver binary.

- **Linux display/X11 issues**
  - Run `xhost +` and retry.

- **LinkedIn verification challenge**
  - Complete verification manually in the browser window, then continue.

- **Missing required file errors**
  - Ensure required filenames are present exactly as listed above.

## Notes

- Keep your personal data in local template files and `.env`; never commit real credentials.
- Respect job platform policies and avoid aggressive automation patterns.

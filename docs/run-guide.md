# Run Guide

## Setup

```bash
cd /path/to/project
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

## Configure

- Copy `.env.example` to `.env`
- Set `LINKEDIN_EMAIL` and `LINKEDIN_PASSWORD`
- Optional: set `OPEN_AI_API_KEY`

## Start

```bash
python3 main.py ./Templates
```

## Common Fixes

- Chrome issue: install Chrome, then retry.
- Linux display issue: run `xhost +`.
- Login challenge: solve in browser, then continue in terminal.

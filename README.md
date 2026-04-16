# Basic Python MySQL Project

## Quick Start

1. Create and activate the virtual environment:

```bash
python3 -m venv .venv
source .venv/bin/activate
```

2. Install dependencies:

```bash
pip install -r requirements.txt
```

3. Copy the environment template and adjust it:

```bash
cp .env.example .env
```

4. Run the project:

```bash
python src/main.py
```

## Structure

- `src/main.py`: entry point
- `src/config.py`: reads database configuration from environment variables
- `src/db.py`: creates a MySQL connection

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

5. Import XML data into MySQL:

```bash
python src/main.py "data/中南科研设计中心建设项目.xml"
```

## Structure

- `src/main.py`: entry point
- `src/config.py`: reads database configuration from environment variables
- `src/db.py`: creates a MySQL connection
- `src/init_db.py`: creates the database schema
- `src/xml_importer.py`: imports XML data into MySQL

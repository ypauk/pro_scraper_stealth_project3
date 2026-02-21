# Professional Async Web Scraper (E-commerce)

A high-performance, modular web scraping system built with **Python** and **Playwright**. Designed with a focus on data integrity, resilience, and ease of configuration.

## 🚀 Key Features
- **Async Engine:** Powered by `asyncio` and `Playwright` for fast, non-blocking data extraction.
- **Resilience:** Built-in **Checkpoint System** (JSON-based) to resume progress from the last page after any interruption or network failure.
- **Data Validation:** Uses **Pydantic** models to ensure 100% accurate data types (prices, ratings, stocks).
- **Flexible Configuration:** All selectors and URLs are managed via a `config.yaml` file—no need to touch the code to change targets.
- **Professional Logging:** Detailed execution logs using `loguru`.

## 🛠 Tech Stack
- **Language:** Python 3.12+
- **Browser Automation:** Playwright (Chromium)
- **Data Handling:** Pydantic, CSV, YAML
- **Logging:** Loguru

## 📁 Project Structure
```text
├── src/
│   ├── models.py       # Data structures & validation
│   ├── parser.py       # HTML parsing logic
│   ├── scraper.py      # Core scraping engine & state management
│   └── settings.py     # Configuration loader
├── config.yaml         # Active configuration (Scraper settings & CSS selectors)
├── main.py             # Entry point
└── data/               # Output directory (CSV & Checkpoints)
```

##Installation & Usage
Clone the repository:
```bash
git clone [https://github.com/your-username/your-repo-name.git](https://github.com/your-username/your-repo-name.git)
cd your-repo-name
```

## Set up virtual environment & install dependencies:

```bash
python -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate
pip install -r requirements.txt
playwright install chromium
```

## Configure the scraper: Edit config.yaml to set your start_url and CSS selectors.

Run the scraper:
```bash
python main.py
```

## 📊 Output Example
The scraper generates a structured CSV file in the data/ folder: | title | price | rating | availability | url | | :--- | :--- | :--- | :--- | :--- | | A Light in the Attic | £51.77 | Three | In stock | https://... |

## Author: Yaroslav Pauk 
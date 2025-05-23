# cse-analytics

<br>⚠️ This repository is **source-available, not open-source.** The code is licensed PolyForm-Strict 1.0.0: no redistribution, no modification, no commercial use. See LICENSE for details.<br>


## Overview

`cse-analytics` is a Python toolkit for scraping, extracting, and analyzing quarterly financial report PDFs from the Colombo Stock Exchange (CSE). It automates the end-to-end workflow: scraping report links, downloading PDFs, extracting structured P&L data using LLMs, merging results, and providing a FastAPI backend for analytics and dashboarding.

---

## Features

- **Automated Scraping**: Uses Playwright and BeautifulSoup to navigate CSE company pages and extract quarterly report links.
- **LLM-Powered Extraction**: Extracts structured financial data from PDFs using Google Gemini (GenAI) models.
- **Concurrent PDF Downloading**: Downloads all company PDFs asynchronously with robust error handling.
- **Data Merging**: Merges extracted JSONs into tidy CSV/Parquet tables for analysis.
- **REST API**: FastAPI backend for orchestrating scraping, extraction, and data access.
- **Dashboard-ready**: Output is suitable for visualization and further analytics.

---

## Project Structure

```
app/
  controllers/         # Core business logic (PDF download, extraction, merging)
  routes/              # FastAPI route definitions
  utils/               # Logging, Google GenAI client, helpers
  models.py            # Pydantic models and schemas
  main.py              # FastAPI app entrypoint
scraping/
  scrape.py            # Playwright-based HTML scraper for CSE company pages
  exract_pdf_links.py  # Extracts quarterly report links from cleaned HTML using Gemini
output/                # Scraped HTML and intermediate files
output_files/          # Extracted financial data JSONs
LICENSE                # PolyForm-Strict 1.0.0
README.md              # Project documentation
```

---

## Workflow

1. **Scrape CSE Company Page**
   - Run `scraping/scrape.py` to navigate to a company's CSE profile, click through to the Quarterly Reports tab, and save cleaned HTML.
   - Output: `output/playwright_explore_rpe/quarterly_reports_tab_cleaned.html`

2. **Extract Quarterly Report Links**
   - Run `scraping/exract_pdf_links.py` to parse the cleaned HTML and extract CDN links to quarterly report PDFs using Gemini.
   - Output: `urls_{company}.json` (e.g., `urls_dpl.json`)

3. **Download PDFs**
   - Use the FastAPI endpoint `/api/v1/download-pdfs/{company_name}` to download all PDFs for a company asynchronously.
   - PDFs are saved in a folder named after the company.

4. **Extract Financial Data from PDFs**
   - Use the FastAPI endpoint `/api/v1/extract-financial-data/` with a POST request containing the company name and directory path.
   - Each PDF is processed via Gemini to extract structured P&L data, saved as JSON.

5. **Merge Extracted Data**
   - Use the FastAPI endpoint `/api/v1/merge-quarterlies` to merge all JSONs in a directory into a single CSV and Parquet file.
   - Output: `rpe_quarterlies.csv`, `rpe_quarterlies.parquet`

---

## API Endpoints

- **POST `/api/v1/download-pdfs/{company_name}`**
  - Triggers background download of all PDFs for a company.
- **POST `/api/v1/extract-financial-data/`**
  - Extracts financial data from all PDFs in a directory for a given company.
- **POST `/api/v1/merge-quarterlies`**
  - Merges all extracted JSONs in a directory into CSV/Parquet.

See [app/routes/](app/routes/) for implementation details.

---

## Chatbot Agent (Agno UI)

This project includes an agentic chatbot built with Agno, which can be accessed via a local web UI.

### 1. Setup and Run the Chatbot Backend

The chatbot backend is defined in `chatbot/agentic_chatbot.py`. To run the chatbot backend:

```sh
uv run python -m chatbot.agentic_chatbot
```

Alternatively, you can use the Makefile command:

```sh
make run-chatbot
```

This will start the Agno agent server, typically on a port like 8000 (as configured in `serve_playground_app`). Ensure your PostgreSQL service (pgvector) is running, as the chatbot uses it for storage. You can start it using:
```sh
make pgvector
```

### 2. Setup and Run the Agno Agent UI

The Agno Agent UI provides a frontend to interact with the chatbot.

**Installation (first time only):**

Use `npx` to create and set up the Agent UI project. This will clone the necessary files and install dependencies.

```sh
npx create-agent-ui@latest
```

Follow the prompts. When asked if you want to install dependencies, you can choose 'y'.

```text
❯ npx create-agent-ui@latest
Need to install the following packages:
create-agent-ui@1.1.6
Ok to proceed? (y) y

       
       
       
        @@@@@@@@@@@@@@@@                                                                            
        @##############@                                                                            
         @@@@@@@@@@@####@                                                                           
                    @####@              @@@@####@@@#@        #@@@@@@@@@#               @@@@@@
                     @####@           @@@######@@@@###@   @###@@@########@@        @@@########@@@
                      @####@        @@###@@@ @@@######@   @###@#@@@ @@@####@     @####@@@ @@@@###@
                       @####@      @####@        @####@   @####@       @####    @###@@        @###@ 
                        @####@     @###@          ####@   @###@        @####@  @####@          @###@
                        @#####@    ####@          @###@   @###@        @####@  @###@           @####
                         @#####@   @###@          ####@   @###@        @####@  @####@          @###@
                          @#####@  @####@        @####@   @###@        @####@   @###@         @####@
@@@@@@@@@@@@@@@            @####@   @####@@@@@@@##@###@   @###@        @####@    @###@@     @@###@@ 
@##############             @####@    @@#######@@ @###@   @####        @####@     @@@##########@@   
@@@@@@@@@@@@@@@              @@@@@@      @@@@@    ####@   @@@@@         @@@@         @@@@@@@@@      
                                   @@@@@@        @####@
                                    @@###@@@@@@@####@
                                       @@@@####@@@@




🚀 Creating a new Agent UI project: agent-ui

Cloning into 'agent-ui'...
remote: Enumerating objects: 114, done.
remote: Counting objects: 100% (114/114), done.
remote: Compressing objects: 100% (109/109), done.
remote: Total 114 (delta 1), reused 48 (delta 1), pack-reused 0 (from 0)
Receiving objects: 100% (114/114), 136.66 KiB | 361.00 KiB/s, done.
Resolving deltas: 100% (1/1), done.

✅ Project cloned successfully!

Do you want to install all dependencies now? (y/n): y

📦 Installing dependencies...
```

**Run the Agent UI:**

Once the `agent-ui` directory is created and dependencies are installed, navigate into it and start the development server:

```sh
cd agent-ui
npm run dev
```

This will typically start the Agent UI on `http://localhost:3000`.

```text
   ▲ Next.js 15.2.3
   - Local:        http://localhost:3000
   - Network:      http://192.168.1.61:3000 # (Network IP may vary)

 ✓ Starting...
 Attention: Next.js now collects completely anonymous telemetry regarding usage.
 This information is used to shape Next.js' roadmap and prioritize features.
 You can learn more, including how to opt-out if you'd not like to participate in this anonymous program, by visiting the following URL:
 https://nextjs.org/telemetry

 ✓ Ready in 1850ms
```

### 3. Using the Chatbot

- Open your browser and navigate to `http://localhost:3000`.
- Connect to your local agent server (usually `http://localhost:8000` or the address shown when you started the chatbot backend).
- You can now interact with the "RAG Agent".

---

## Scraping & Extraction Scripts

- **scraping/scrape.py**: Uses Playwright to automate browser navigation and save cleaned HTML of the Quarterly Reports tab.
- **scraping/exract_pdf_links.py**: Uses Gemini to extract quarterly report links from HTML and outputs a JSON file.

---

## LLM Extraction

- **app/controllers/data_extractor_controller.py**: Handles interaction with Google Gemini for extracting structured financial data from PDFs.
- **app/routes/extract_data.py**: Orchestrates batch extraction for all PDFs in a directory.

---

## Data Merging

- **app/controllers/merge_financials_controller.py**: Merges all extracted JSONs into a tidy DataFrame, outputs CSV and Parquet.
- **app/routes/merge_financials.py**: API endpoint for merging and previewing results.

---

## Logging & Error Handling

- Uses `structlog` for structured logging.
- All major steps log progress and errors for traceability.
- Failed downloads and extraction errors are logged and saved for review.

---

## Requirements & Setup

- Python 3.13+
- Install dependencies using [uv](https://docs.astral.sh/uv/):
  ```sh
  uv sync
  ```
- Set up Google Gemini API credentials in your environment (see `.env` usage in scripts).
- For scraping, install Playwright and its browser drivers:
  ```sh
  uv pip install playwright
  playwright install
  ```

---

## Licensing

This repository is licensed under the [PolyForm Strict License 1.0.0](https://polyformproject.org/licenses/strict/1.0.0):
- **No redistribution**
- **No modification**
- **No commercial use**
- **Source-available for personal, research, and noncommercial institutional use only**

See [LICENSE](LICENSE) for full terms.

Copyright © 2025 Amod

# Pathway Live Demo

Pathway is a candidate and employer decision support prototype for Australian career and migration intelligence.

## What this build includes

* Resume upload for PDF, DOCX and TXT
* Editable profile extraction
* Candidate dashboard and Employer lens
* Progressive intelligence modules with independent source status
* Live Department of Home Affairs SkillSelect page check
* Live Jobs and Skills Australia occupation and shortage source checks
* Live Jobs and Skills Australia Internet Vacancy Index source check
* Job provider adapter with Adzuna support when API credentials are supplied
* Visible fallback state when a live job provider is not configured
* TTL caching so refresh does not hammer every source
* Source freshness and failure labels
* Visa context aware recommendation engine for student, working holiday, offshore and experienced profiles

## Important data integrity decisions

This prototype does not claim that SEEK or LinkedIn have public unrestricted vacancy APIs. It does not scrape those sites and does not fabricate a live vacancy count.

The live source adapters check official source pages at request time and cache responses for defined periods. For a production system, replace page parsing with official APIs, data downloads, licensed feeds or scheduled ingestion jobs wherever available.

The vacancy chart is marked in the API as `interface_preview` until the published JSA IVI spreadsheet ingestion pipeline is implemented. The page itself is checked live, but the chart series should not be presented to users as a live occupation specific count in production.

ANZSCO and OSCA should both be supported during Australia's classification transition. JSA has stated that ANZSCO occupation profile data will no longer be updated and newer occupation profile work is moving to OSCA.

## Run locally

### Backend

```bash
cd backend
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
uvicorn main:app --reload --port 8000
```

On Windows PowerShell use `.venv\\Scripts\\Activate.ps1` instead of the `source` command.

### Frontend

```bash
cd frontend
npm install
npm run dev
```

Open http://localhost:5173

## Optional live job feed

Set these environment variables before starting the backend:

```text
ADZUNA_APP_ID=your_id
ADZUNA_APP_KEY=your_key
```

The adapter is isolated so another licensed Australian job data provider can be substituted later.

## Recommended production architecture

Use Postgres for user profiles and recommendation history, Redis for freshness aware caching, object storage for encrypted resume uploads, a queue such as Celery or Dramatiq for source refresh jobs, and a data warehouse for historical invitation and labour market series. Store source provenance with every metric. The recommendation layer should consume normalised facts with timestamps rather than scraping pages directly.

For migration data, maintain strict separation between official facts, model interpretation and legal advice. Recommendations must always link back to the source and show when it was checked.


## September 2026 UX upgrade

The Highest impact next move card now opens a subscription modal from Build Evidence Plan. The demo presents Plus at A$10 per month and Premium at A$20 per month. Checkout remains intentionally non transactional in this prototype.

The Live intelligence check panel now surfaces a result summary as each source completes, including SkillSelect round or occupation score information, occupation shortage status, the current IVI release signal, and personalised job result count and top match. Source status and freshness remain visible alongside the result.

The dashboard now also updates intelligence modules progressively as each request completes instead of waiting for all four requests before showing any source output.


## Dynamic pathway progression

The pathway map now progresses from the candidate profile rather than always starting at step one. It uses occupation resolution, classification evidence, skill depth, relevant experience, qualification detail, visa context and live market coverage to determine which stages are complete and which stage is current. A candidate with stronger aligned experience can therefore enter later in the pathway than a student or early career profile.

## Rich intelligence cards

The dashboard vacancy, shortage and subclass 189 cards now expose decision useful facts rather than status only. Vacancy intelligence parses the current JSA IVI release period, release date and next published release date. Shortage intelligence discovers the current JSA Occupation Shortage List workbook, attempts occupation and state matching, and also exposes national shortage context and the latest vacancy fill rate. SkillSelect intelligence parses the current Home Affairs subclass 189 round, invitation count, occupation minimum score when matched, next expected round and program year invitation context when available.

The JSA workbook parser requires `openpyxl`, which is included in `backend/requirements.txt`. Reinstall backend requirements after upgrading.

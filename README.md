# Pathway: career fit, market evidence and PR roadmap

## App structure

The dashboard has three sections: **Home**, **Jobs** and **Visa**. The layout follows Apple's Human Interface Guidelines: few top-level sections, the most important content first, progressive disclosure, and badges only for urgent items.

* **Home**: your one next step (from the active visa plan, with its first task and a direct action), three numbers (visa days left, points, matching jobs), the next three steps and your top three job matches. A banner lists missing answers.
* **Jobs**: advert search and evidence, plus a Demand card with JSA shortage ratings (formerly the Market tab).
* **Visa**: the PR navigator (My plan, Compare routes, Points, Checks & deadlines, States & evidence). The tab badge appears only for a high-severity deadline within 90 days.
* **Profile** (avatar in the sidebar, or top right on mobile) opens a panel with your resume summary (with a link back to the review screen) and the answers a resume cannot provide: visa expiry, date of birth, relationship, English, skills assessment, NAATI, Professional Year, sponsorship, regional willingness and target states. These answers are not repeated anywhere else.
* **Sources**: a header button ("2 of 4 sources live") opens the source list. It replaces the panel that used to repeat on every tab.

The My pathway and Market tabs and Employer mode were removed. Their generic or empty content repeated what the other sections show.

## Landing and resume review

* **Landing page.** Drag and drop or choose a resume (PDF, DOCX or TXT). Progress steps show while it is read, and a "Continue as ..." button appears for a saved profile.
* **Section-aware parser** (`backend/resume_parser.py`). It splits the resume into its own sections, then reads entries anchored on date ranges. Experience comes only from each role's own dates; the old parser subtracted the earliest year anywhere in the text, so a standard such as AS 4254.2-2012 produced "14 years". Volunteering is separated even when it sits inside Experience. Education is read with its major or concentration and level, and high school is excluded from migration. Projects keep their tools. Achievements, publications, certifications, grouped skills, contact details and location are also extracted. DOCX tables are read as well.
* **Occupation mapping** (`backend/occupations.py`). Occupations are suggested from the summary, degree major, recent roles and projects, each with its reasons. Every suggestion carries its ANZSCO code and assessing authority behind the scenes, so the candidate never types a code. A full catalogue and a free-text option are also available.
* **"Check what we found" screen.** People can edit their details, visa and expiry. Work experience shows each role's duration and three totals: paid experience (overlaps counted once), experience relevant to the chosen occupation (ticked per role), and relevant experience after graduation (which counts for migration points). Roles are tagged as internship, overseas, remote or before graduation, and can be edited, added or removed. Volunteering is listed but not counted. The screen also covers education with major, projects with matching evidence, achievements and certifications, editable skills, and optional goals. Confirming fills the profile, the migration answers (qualification, field of study, completion date, Australian and overseas post-graduation experience, and whether the person currently works in their field) and the job search.

## Migration tab: PR navigator

The Migration tab is now a full planner. It turns the reviewed profile plus a short set of migration answers into dated routes to permanent residence.

* **Your circumstances.** Four short groups: You, Study, English and skills, Work and preferences. Rarely needed fields sit under "More details". Field of study picks the assessing authority: Engineering goes to Engineers Australia, IT or data science to ACS, accounting to CPA/CA ANZ/IPA, nursing to ANMAC, teaching to AITSL, trades to TRA, and anything else to VETASSESS. Employer sponsorship is a Yes/No question. Answering No hides every sponsored route. Answers update the plan straight away and are saved in the browser. A parsed resume pre-fills institution, field of study, qualification, completion month, English score and NAATI.
* **My plan.** Two track cards, Independent (189, 190, 491) and Employer sponsored (482 to 186, 494), plus a Partner card when it applies. The chosen route shows its PR window, charges and progress, then only the next three steps (each step expands to show tasks, links and costs). The full timeline and every step are one click away. You can export to a calendar (.ics) or print.
* **Compare routes.** Routes grouped by track, a comparison table, and a "Routes ruled out for you" list that explains each exclusion. The decision tree is behind a toggle.
* **Points.** Your verified total and its breakdown. The what-if panel starts from your saved answers, now including Australian study and regional campus. It also shows points over 6 years, and lets you set your own 189 target when no minimum is published.
* **Checks and deadlines.** The deadline register, plus per-visa criteria marked met, a later step, needs an answer, or not met.
* **States and evidence.** State programs, JSA ratings, job-advert work rights, planning levels, thresholds and provenance.

**Feasibility rules.** A route is ruled out, not shown as a stretch, when it cannot work on the visa time available. For example, 186 Direct Entry and 494 need 3 years of experience before applying. A 485 graduate has at most 2 years (3 after a research degree), minus the time to find work, so those routes are excluded with the reason given, and the 482 then 186 route is pointed to instead. Routes are also excluded for age 45 or over, for "No" to regional living (491, 494), and for "No" to sponsorship.

Elsewhere in the app: Overview has a PR roadmap card. My pathway lists the migration milestones of the active plan. Jobs now flags adverts that are citizens or PR only, need a security clearance, require work rights or mention sponsorship (quoted evidence), and the planner uses those counts. On narrow screens, a section bar replaces the hidden sidebar.

### Where the rules come from

`backend/migration_rules.py` is a versioned rulebook (version `2026.10-1`, verified 8 Oct 2026). It records the current points table, visa criteria, 1 July 2026 charges, CSIT/SSIT/TSMIT, 2026-27 planning levels, assessing authorities, state program notes and Australian institutions, each with a source. There is no machine-readable feed for these rules, so they are curated rather than invented, and every value shows its basis in the UI.

These parts are checked live on each request and cached: the SkillSelect round and occupation minimum, JSA shortage ratings, the "From AUD" charge on each Home Affairs visa page, and an excerpt from each state program page. If a live check fails, the rulebook value is used and labelled as such. The points test reform announced in the 2026-27 Budget is not legislated, and the UI warns about it.

Dates are estimates built from published processing ranges and the stated assumptions (for example, "skilled employment starts about 3 months after graduation"). They are not forecasts of invitations. This is decision support, not migration advice.

### Updating the rulebook

Edit `backend/migration_rules.py`, change `RULEBOOK_VERIFIED`, then run `pytest tests -q` and `npm run test:migration`. Regenerate `frontend/scripts/fixtures/plan.json` if the plan shape changes.

This version keeps the corrected Overview and adds an evidence based Jobs tab. A shared collection of adverts describes employer demand, while each client receives a separate comparison against their reviewed resume profile.

## What changed

* Removed the unsupported pathway readiness percentage, opportunity uplift numbers and fabricated job fit percentages.
* Added a checklist that counts supplied profile fields. This is not a measure of employability, migration points or visa eligibility. A code entered in the profile is not a verified skills assessment.
* Home Affairs extraction decodes the hidden PageSchema JSON and reads the published invitation tables. Round dates, invitation totals, occupation minimums and tie break dates retain their context. An absent occupation row is distinct from a failed source request.
* JSA shortage extraction discovers the latest six digit occupation workbook, keeps ANZSCO and OSCA codes separate, and reads national and state ratings. S, NS, R and M are decoded explicitly. There is no fuzzy title match or shortage inference from page mentions.
* Added a persistent SQLite job cache and on demand Apify task runs for new role and location searches. Existing completed results are imported when their original scope can be verified.
* Jobs now shows sample counts by seniority, hiring companies, advertised salary ranges, skills mentioned at each level and advert evidence. Profile comparisons explain supported skills, evidence gaps and stated experience requirements.
* Replaced invented job match percentages with transparent labels: strong evidence alignment, potential fit, stretch and needs review. These are rule based comparisons, not hiring probabilities.
* Preserved the legacy read only jobs endpoint, including optional Adzuna support, for compatibility. The new Jobs tab and Overview job cards use the new Apify search pipeline.
* Removed the illustrative vacancy chart data. IVI remains publication metadata only; occupation vacancy time series is not connected.
* Source failures load independently. Cached partial data remains partial. Occupation caches include the selected state and classification codes.
* Resume uploads no longer inherit the sample profile occupation codes. Editing the target occupation clears the old codes and candidate roles so unrelated statistics cannot follow a changed occupation silently.

Other tabs retain their existing prototype behaviour. In particular, the migration route rankings and employer examples are not validated assessments. This update focuses on Overview, Jobs and shared data integrity.

## Start on Windows

Use standard Windows CPython. If the old environment was created with MSYS2 Python, create a new environment in this extracted folder with the Windows Python launcher.

In one PowerShell window:

```powershell
cd backend
py -3.12 -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
Copy-Item .env.example .env
.\.venv\Scripts\python.exe -m uvicorn main:app --reload --port 8000
```

Copy `.env.example` only when creating a new `.env`; keep existing credentials if one already exists. The backend loads `.env` automatically. Restart it after changing provider settings.

In another PowerShell window:

```powershell
cd frontend
npm ci
npm run dev
```

Open http://localhost:5173. The frontend proxies `/api` to the backend on port 8000. The locked frontend packages require Node 20.19 or a supported version from 22.12 onward.

On macOS or Linux, create the environment with `python3 -m venv .venv`, then use `.venv/bin/python` in place of the Windows interpreter path.

## Connect the saved Apify task

The app is configured for `curious_coder/linkedin-jobs-scraper`, actor `hKByXkMQaC5Qt9UMN`.

Your saved task is `FcJaZmFO4ABzrGRZ1`. The earlier `aScBU8lDVTdbXEDWQ` is a completed run, not a task. Both nonsecret identifiers are already in `.env.example`.

1. In Apify, create a separate personal API token for Pathway. A default token can authenticate too; a separate token can be revoked without affecting other integrations.
2. Put the token in `backend/.env` as `APIFY_TOKEN`. Keep it out of chat, frontend code and version control. If restricting permissions, allow reading the saved task, runs, their default datasets and the `INPUT` record in their default key value stores. Starting new collections also needs permission to run the actor/task.
3. Restart the backend and analyse your profile. The first search attempts to import the existing run. No new run starts while `APIFY_ENABLE_RUNS=false`.
4. Check the collection banner in Jobs. Import verifies the original role, location, date window, radius and restrictions from the run's saved input. It does not assign an Australia wide run to Brisbane or a junior only run to all levels. The run may be older than the cache's freshness window; such results remain marked older.
5. To enable the requested pipeline for new searches, set `APIFY_ENABLE_RUNS=true` and restart the backend. Review the small initial limits below.

```text
APIFY_TOKEN=your_private_personal_token
APIFY_TASK_ID=FcJaZmFO4ABzrGRZ1
APIFY_SEED_RUN_ID=aScBU8lDVTdbXEDWQ
APIFY_ENABLE_RUNS=true
APIFY_SEARCH_LIMIT=10
APIFY_MAX_AGE_HOURS=48
APIFY_MAX_CHARGE_USD=0.50
APIFY_DAILY_RUN_LIMIT=5
APIFY_RUN_TIMEOUT_SECONDS=180
```

This starts with 10 adverts per search, a 48 hour freshness window, at most five attempted new collections per UTC day, a US$0.50 maximum run charge sent to Apify, and a 180 second actor timeout. Actor prices or minimum charges can make the configured charge limit insufficient; a rejected or failed run stays visible. Read requests and unrelated runs in your Apify account are outside this app's run ledger. Increase limits only after inspecting the initial results. No live run has been started from the development environment.

LinkedIn Premium and account cookies are not used by this public jobs actor integration. Only role, Australian location, advert date window and collection options are sent to Apify. Resume text, candidate identity, skills and experience stay in the Pathway backend during personal comparison.

### What happens when a client searches

1. `POST /api/jobs/search` normalises the role and Australian location. The cache key also includes source, query version, collection size, 25 mile radius and advert date window. City and state searches are different. Experience level is a local filter so one collection supports comparisons across all levels.
2. A recent matching collection is reused, including a valid empty collection. The persistent corpus is shared; profiles and personal fit results are not stored in that corpus.
3. For a miss or stale collection, the backend checks the run budget and atomically reserves the query before creating one run. Simultaneous clients reuse that run. POST input overrides saved keywords, location, URLs and other search filters without modifying the saved task. Company detail scraping and location splitting are disabled.
4. The response immediately reports the persisted collection state. The frontend polls the same search to read that run and retrieve its successful dataset. A normal poll cannot start another run. A poll waiting for the first seed import may complete the original authorised search once that read finishes.
5. Successful results are saved with run ID, original query, collection time and raw advert evidence. Each client's fit explanations are recalculated separately. Known expired or closed ads and duplicate canonical listing URLs are removed when analysed.
6. Stale data remains visible during refresh. Failed runs do not replace it. After restart, the next request resumes checking a persisted run; an open browser is not required for the Apify actor to finish. Importing results after completion requires a subsequent request.

The browser form starts with the desired role and full location from profile review. Changing seniority changes counts, companies, salary groups, skills and matches locally without another scrape. Related role buttons use the reviewed resume's suggested roles and initiate a separate search if selected. Changing a personal skill does not make a new corpus necessary.

### Existing run scope and recovery

The importer understands structured keywords/location inputs and a single classic LinkedIn search URL with explicit keywords/location and supported date filters. Multiple URLs, unknown geo IDs, restricted company or seniority filters, nonstandard radii or missing scope are not silently reused. If the existing run cannot be read, the app pauses new collection requests instead of paying for a possible duplicate. Correct its read permissions, or clear `APIFY_SEED_RUN_ID` if you intentionally want to skip importing it. If the import cannot verify scope, export the run's `INPUT` JSON and a few dataset rows with secrets removed so the adapter can be extended accurately. The private task and run have not been inspected from this environment because no token was supplied.

An uncertain response to a paid POST is never retried automatically. If Jobs reports an unconfirmed run start, inspect the task's runs in Apify. If a run exists, set `APIFY_SEED_RUN_ID` to that run and restart to import it. If you have confirmed that no run exists, reset only that query using its `queryId` from the search response:

```powershell
.\.venv\Scripts\python.exe jobs_admin.py YOUR_QUERY_ID --confirmed-no-run
```

Budget reservations are retained after a failed or uncertain attempt. Definitively failed collections have a one hour retry cooldown. The ledger and cached data live in `backend/data/jobs.sqlite3` by default; keep that directory between restarts and configure `JOBS_CACHE_PATH` to a durable shared path when hosting. Do not delete the database to bypass limits.

### How to interpret the intelligence

Counts are distinct active adverts in a bounded sample from one provider search, not the total number of jobs in an occupation or city. The provider can return related titles and nearby locations. Job titles and exact locations remain visible for review. A 25 mile radius is about 40 kilometres. Reposts with a new job ID may remain separate; deduplication does not prove unique employer headcount. When the sample limit is reached, the banner says so.

Seniority uses explicit title, a clear provider label or a detected minimum experience requirement. An inference from years uses 0 to 2 for junior, 3 to 5 for mid level and 6 or more for senior. Leadership and unspecified have their own buckets. Ambiguous labels such as `Mid-Senior level` or `Associate` remain unspecified unless another signal resolves them. Junior titles that ask for at least three years stay junior and are highlighted with the advert quote. Classification is a heuristic, not an official occupation level.

Skills are detected with the visible starter vocabulary in `backend/job_analysis.py`. Frequency means adverts mentioning the skill, not necessarily requiring it. Counts are independent of an individual profile. This first version is strongest for engineering and technology; vocabulary coverage for other occupations is incomplete. Additional supplied skills can contribute to a personal match without changing shared market counts. No external language model is used. Resume extraction is also heuristic, and experience inferred from resume dates needs review.

Personal fit uses title alignment, supplied skills detected in the advert and stated experience. A shortfall in years, or an explicitly senior title with a very early career profile, marks a role as a stretch. Strong evidence alignment requires a matching title, detected skills all supported and a stated experience minimum met by the reviewed profile. These comparisons cannot verify relevant experience, qualifications, licences, work rights or hiring outcomes. “Not evidenced” means absent from the supplied skills, not that the person lacks the skill. No perfect job claim is made.

Pay remains in its advertised currency, pay period and super/package basis. Ranges show the lowest and highest observed endpoints with the number of contributing adverts. Hourly and annual amounts are not converted or mixed. A bare dollar sign stays currency unstated; amounts without a clear pay period are not included in numeric comparisons. Salary parsing is conservative and will miss some formats. Missing pay is never zero.

The AI panel reports detected mentions and explicit experience requirements with source links. A single sample cannot establish falling junior hiring or an AI caused increase in expectations. Raw snapshots are retained for future comparable series, but trend analysis and causal inference are not implemented.

### Hosting scope

This is a local prototype, not a public multi tenant service. Before public launch, add authenticated clients, per client rate limits and quotas, an operational collection queue, retention controls and an access controlled API. CORS defaults to local frontend origins; configure `FRONTEND_ORIGINS` when hosting. Global collection caps protect the prototype's provider usage but do not replace client authentication. All backend workers must share the same SQLite file for deduplication; a multi instance deployment needs a shared database/queue.

Apify references used for the adapter:

* https://apify.com/curious_coder/linkedin-jobs-scraper/input-schema
* https://docs.apify.com/api/v2/actor-task-runs-post
* https://docs.apify.com/api/v2/actor-run-get
* https://docs.apify.com/api/v2/dataset-items-get
* https://docs.apify.com/integrations/api

## Official source behaviour

Home Affairs is read directly from its public invitation round page, including the embedded accordion content. Occupation scores are matched by exact official title. Where the supplied ANZSCO code can be resolved in the JSA workbook, that official title is used and displayed. If mapping cannot be verified, the app does not borrow another occupation's score. Published historical minimums are not future thresholds.

JSA discovery reads https://www.jobsandskills.gov.au/data/occupation-shortage and then the latest linked occupation workbook. It does not require the separate profile or shortage report pages to succeed. Rating year, classification, official occupation, national rating, state rating, source link, workbook link and retrieval time are displayed when available. A workbook download or parsing failure remains unavailable.

In this development environment, the Home Affairs page was retrieved and the parser extracted the 4 June 2026 round with 10,000 invitations and 140 occupation rows. JSA requests timed out or returned an upstream 502, so the real current workbook could not be validated here. The workbook parser was tested against representative XLSX layouts; confirm the live workbook results on your machine before presenting them. These observations are validation notes, not bundled production data or fallbacks.

No historical fixture is silently substituted for live source data. Source metadata and parsed public datasets are cached, with retrieval timestamps retained. A cached response is shown as such. Backend restart clears the in memory official source caches. The job corpus and run ledger persist in SQLite.

## Verification

```powershell
cd backend
.\.venv\Scripts\python.exe -m pip install -r requirements-dev.txt
.\.venv\Scripts\python.exe -m pytest tests -q
```

```powershell
cd frontend
npm run test:overview
npm run test:jobs
npm run test:migration
npm run test:review
npm run build
```

The backend checks cover hidden Home Affairs content, 189 versus 491 columns, previous rounds, real zero values, code namespaces, state ratings, unmatched occupations, failed sources, cache keys, profile counting and Apify authentication, pagination, stale results, unknown collection dates, missing configuration and empty datasets. Frontend component checks cover the corresponding visible states. Job pipeline checks additionally cover simultaneous clients, seed import races, query isolation, personal result isolation, persistent run recovery, paid run limits, uncertain POST handling, stale and empty collections, salary units, seniority ambiguity and evidence links. Live Apify testing requires your credentials and a completed dataset.

A browser preview was not available in the development environment. The production build and component rendering checks are provided without claiming a completed visual browser review.

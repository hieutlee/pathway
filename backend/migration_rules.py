"""Versioned migration rulebook.

Australian visa criteria are published as prose and legislative instruments, not as a
machine-readable feed. This file is the single, auditable place where Pathway records the
rules it applies. Every value carries a source and the date it was last verified, so the
interface can show provenance next to the figure. Where a live check is possible
(visa charges, state program notices, invitation rounds, shortage ratings) the engine
prefers the live value and falls back to this rulebook with its verification date shown.

Update procedure: change the value, update `verified`, add the source, run the tests.
"""
from __future__ import annotations

RULEBOOK_VERSION = "2026.10-1"
RULEBOOK_VERIFIED = "2026-10-08"

HA = "https://immi.homeaffairs.gov.au"
VISA_URL = {
    "500": f"{HA}/visas/getting-a-visa/visa-listing/student-500",
    "485": f"{HA}/visas/getting-a-visa/visa-listing/temporary-graduate-485",
    "482": f"{HA}/visas/getting-a-visa/visa-listing/skills-in-demand-482",
    "186": f"{HA}/visas/getting-a-visa/visa-listing/employer-nomination-scheme-186",
    "494": f"{HA}/visas/getting-a-visa/visa-listing/skilled-employer-sponsored-regional-494",
    "189": f"{HA}/visas/getting-a-visa/visa-listing/skilled-independent-189",
    "190": f"{HA}/visas/getting-a-visa/visa-listing/skilled-nominated-190",
    "491": f"{HA}/visas/getting-a-visa/visa-listing/skilled-work-regional-provisional-491",
    "191": f"{HA}/visas/getting-a-visa/visa-listing/permanent-residence-skilled-regional-191",
    "820": f"{HA}/visas/getting-a-visa/visa-listing/partner-onshore",
    "858": f"{HA}/visas/getting-a-visa/visa-listing/national-innovation-visa-858",
}
POINTS_TABLE_URL = f"{HA}/visas/working-in-australia/skillselect/points-table"
SKILLSELECT_URL = f"{HA}/visas/working-in-australia/skillselect"
PROCESSING_URL = f"{HA}/visas/getting-a-visa/visa-processing-times/global-visa-processing-times"
PRICING_URL = f"{HA}/visas/visa-pricing-estimator"
PLANNING_URL = f"{HA}/what-we-do/migration-program-planning-levels"
REGIONAL_URL = f"{HA}/visas/working-in-australia/regional-migration/eligible-regional-areas"
ENGLISH_URL = f"{HA}/help-support/meeting-our-requirements/english-language"
VEVO_URL = f"{HA}/visas/already-have-a-visa/check-visa-details-and-conditions/check-conditions-online"
SECONDARY = {
    "fees": ("RACC summary of 1 July 2026 visa charges", "https://www.racc.net.au/single-post/australia-visa-fee-increase-1-july-2026"),
    "485": ("Australian Migration Lawyers 485 guide (2026)", "https://www.australianmigrationlawyers.com.au/news-and-updates/temporary-graduate-visa-485-guide-2025"),
    "thresholds": ("EIG: CSIT, SSIT and TSMIT from 1 July 2026", "https://eiglaw.com/australia-skilled-visa-income-thresholds-rise-july-2026/"),
    "planning": ("RACC: 2026-27 planning levels", "https://www.racc.net.au/single-post/australia-migration-program-planning-levels-2026-27"),
    "trt": ("Wave: 186 TRT work experience change from 29 Nov 2025", "https://wave.com.au/blog/changes-to-work-experience-requirements-for-186-trt-applicants-from-29-november-2025"),
    "pte": ("PTE equivalence from 7 August 2025", "https://pathwaytoaus.com/general/australia-visa-pte-score-changes-take-effect-august-7-2025/"),
    "processing": ("immi.tv processing time summary (DHA data, 2026)", "https://immi.tv/australia/skilled-visas/processing-times-2026/"),
    "reform": ("RACC: points test reform in the 2026-27 Budget", "https://www.racc.net.au/single-post/australia-skilled-migration-points-test-changes-2026-federal-budget"),
    "assessment_fees": ("WIDEN: skills assessment fees, checked Aug 2026", "https://www.widen.com.au/skills-assessment-fees/"),
    "states": ("WIDEN state nomination tracker, 3 Oct 2026", "https://www.widen.com.au/state-nomination-tracker/"),
    "191": ("visaplan: subclass 191 in 2026", "https://visaplan.au/blog/subclass-191-pr-for-491-and-494-holders-in-2026/"),
    "858": ("One Planet: National Innovation visa 2026", "https://oneplanetmigrationlaw.com.au/immigration-blog/national-innovation-visa-858-2026/"),
    "partner": ("One Planet: 820/801 guide 2026", "https://oneplanetmigrationlaw.com.au/immigration-blog/partner-visa-820-801-complete-guide-2026/"),
    "494": ("OneU: 494 visa guide", "https://www.oneuedu.com/en-US/visa/494-skilled-employer-sponsored-regional-visa"),
}

# ---------------------------------------------------------------------------
# Visa catalogue. Fees are the primary applicant base charge from 1 July 2026.
# Processing ranges are indicative published ranges, not promises.
# ---------------------------------------------------------------------------
VISAS = {
    "500": {"name": "Student", "kind": "temporary", "stage": 0, "fee": 2500,
            "processing": "Varies by sector and country", "processingMonths": (1, 4),
            "stay": "Length of the course plus a short period after it ends",
            "rights": "Work up to 48 hours per fortnight while the course is in session (condition 8105); unlimited in scheduled breaks and after the course ends while the visa is valid.",
            "keyConditions": ["8105 work limit 48 hours per fortnight in session", "Maintain enrolment and satisfactory progress", "Overseas Student Health Cover"],
            "notes": ["Since 1 July 2024, 485 and visitor visa holders cannot apply for a student visa from inside Australia."]},
    "485": {"name": "Temporary Graduate", "kind": "temporary", "stage": 1, "fee": 5750,
            "processing": "Post-Higher Education: typically 3 to 5 months", "processingMonths": (3, 5),
            "stay": "Bachelor or coursework masters: up to 2 years. Research masters or PhD: up to 3 years. Post-Vocational: up to 18 months.",
            "rights": "Full work rights. No sponsor needed.",
            "keyConditions": ["Overseas Visitor Health Cover (OSHC does not count)", "Lodge in Australia within 6 months of course completion", "One Post-Higher Education grant as a primary applicant"],
            "notes": ["Charge rose to $4,600 on 1 March 2026 and $5,750 on 1 July 2026.", "A second Post-Higher Education stream ($2,265) adds 1 year (Category 2 regional) or 2 years (Category 3 regional) for graduates who studied and lived regionally."]},
    "482": {"name": "Skills in Demand", "kind": "temporary", "stage": 2, "fee": 4015,
            "processing": "Typically weeks to a few months; accredited sponsors are faster", "processingMonths": (1, 4),
            "stay": "Up to 4 years",
            "rights": "Work for the approved sponsor in the nominated occupation. A new nomination is needed before changing employer.",
            "keyConditions": ["Core Skills: CSOL occupation and salary at least CSIT ($79,423) and market rate", "Specialist Skills: salary at least SSIT ($146,576)", "At least 1 year of relevant work experience", "Labour market testing by the employer for Core Skills"],
            "notes": ["Employer also pays sponsorship ($420), nomination ($330) and the Skilling Australians Fund levy."]},
    "186": {"name": "Employer Nomination Scheme", "kind": "permanent", "stage": 3, "fee": 6140,
            "processing": "Transition stream 4 to 10 months; Direct Entry 7 to 18 months (75th percentile)", "processingMonths": (4, 18),
            "stay": "Permanent", "rights": "Permanent residence: live, work and study anywhere in Australia; Medicare; citizenship after the residence requirement.",
            "keyConditions": ["Under 45 at application (limited exemptions)", "Competent English", "Salary at least CSIT and market rate"],
            "notes": ["Transition stream: 2 years working for an approved sponsor while on 482 or 457. Since 29 November 2025 only time with an approved sponsor counts.", "Direct Entry: 3 years of relevant experience, positive skills assessment and an occupation on the CSOL."]},
    "494": {"name": "Skilled Employer Sponsored Regional", "kind": "provisional", "stage": 2, "fee": 6140,
            "processing": "Employer stream: median about 8 months, 90% within 12 months", "processingMonths": (8, 12),
            "stay": "5 years", "rights": "Live and work only in a designated regional area for the sponsor.",
            "keyConditions": ["Under 45", "3 years of full-time skilled experience", "Positive skills assessment", "Competent English", "Salary at least TSMIT ($79,423) and market rate"],
            "notes": ["Leads to subclass 191 after 3 years of complying with regional conditions."]},
    "189": {"name": "Skilled Independent", "kind": "permanent", "stage": 3, "fee": 6135,
            "processing": "5 to 14 months (75th percentile)", "processingMonths": (5, 14),
            "stay": "Permanent", "rights": "Permanent residence with no sponsor or location obligation.",
            "keyConditions": ["Invitation through SkillSelect", "Under 45 at invitation", "At least 65 points", "Occupation on MLTSSL", "Positive skills assessment", "Competent English"],
            "notes": ["Invitations go to the highest ranked EOIs per occupation; the pass mark is a floor, not a target."]},
    "190": {"name": "Skilled Nominated", "kind": "permanent", "stage": 3, "fee": 6140,
            "processing": "6 to 12 months (75th percentile)", "processingMonths": (6, 12),
            "stay": "Permanent", "rights": "Permanent residence; most states ask for a 2 year commitment to live and work there.",
            "keyConditions": ["State or territory nomination (+5 points)", "Under 45 at invitation", "At least 65 points", "Occupation on the state's list", "Positive skills assessment", "Competent English"],
            "notes": ["State criteria change each program year and programs open and close."]},
    "491": {"name": "Skilled Work Regional", "kind": "provisional", "stage": 2, "fee": 6140,
            "processing": "5 to 12 months (75th percentile)", "processingMonths": (5, 12),
            "stay": "5 years", "rights": "Live, work and study only in a designated regional area (condition 8579).",
            "keyConditions": ["State nomination or eligible family sponsorship (+15 points)", "Under 45 at invitation", "At least 65 points", "Positive skills assessment", "Competent English"],
            "notes": ["2026-27 planning level cut to 14,110 places (from 33,000).", "Leads to subclass 191 after 3 years."]},
    "191": {"name": "Permanent Residence Skilled Regional", "kind": "permanent", "stage": 3, "fee": 630,
            "feeNote": "Rulebook value from a secondary source; confirm in the Visa Pricing Estimator.",
            "processing": "Not reliably published; check the global processing times page", "processingMonths": (3, 9),
            "stay": "Permanent", "rights": "Permanent residence; regional obligation ends.",
            "keyConditions": ["Held 491 or 494 for at least 3 years while complying with regional conditions", "ATO notices of assessment for 3 income years", "No minimum income amount is currently specified"],
            "notes": []},
    "820": {"name": "Partner (onshore, 820 then 801)", "kind": "provisional", "stage": 2, "fee": 11710,
            "processing": "820: median about 17 months, 90% within 24 months", "processingMonths": (17, 24),
            "stay": "820 is temporary until 801 is decided, generally about 2 years after lodgement",
            "rights": "Work and study while the application is processed (bridging visa A in most cases).",
            "keyConditions": ["Sponsor is an Australian citizen, permanent resident or eligible NZ citizen", "Married, or de facto for 12 months (registration in QLD, NSW, VIC, ACT, TAS or SA waives the 12 months)", "No 8503 'No Further Stay' condition on your current visa"],
            "notes": ["One charge covers both stages."]},
    "858": {"name": "National Innovation", "kind": "permanent", "stage": 3, "fee": None,
            "feeNote": "Check the Visa Pricing Estimator.",
            "processing": "Varies; invitation based", "processingMonths": (3, 12),
            "stay": "Permanent", "rights": "Permanent residence.",
            "keyConditions": ["Invitation after an expression of interest", "Internationally recognised record of exceptional and outstanding achievement", "Australian nominator with a national reputation in the field"],
            "notes": ["April to June 2026: 2,166 EOIs and 248 invitations, mostly Priority 3 (Tier One sector achievements)."]},
}

# ---------------------------------------------------------------------------
# Points table (Home Affairs, in force; reform announced but not legislated).
# ---------------------------------------------------------------------------
PASS_MARK = 65
AGE_POINTS = [(18, 24, 25), (25, 32, 30), (33, 39, 25), (40, 44, 15)]
ENGLISH_POINTS = {"competent": 0, "proficient": 10, "superior": 20}
AU_EXPERIENCE_POINTS = [(8, 20), (5, 15), (3, 10), (1, 5)]
OS_EXPERIENCE_POINTS = [(8, 15), (5, 10), (3, 5)]
EXPERIENCE_CAP = 20
QUALIFICATION_POINTS = {"doctorate": 20, "masters_research": 15, "masters_coursework": 15, "bachelor": 15, "diploma": 10, "trade": 10}
BONUS_POINTS = {"australianStudy": 5, "specialistEducation": 10, "professionalYear": 5, "naati": 5, "regionalStudy": 5}
PARTNER_POINTS = {"single": 10, "partner_citizen_pr": 10, "partner_skilled": 10, "partner_competent_english": 5, "partner_other": 0}
NOMINATION_POINTS = {"190": 5, "491": 15}

ENGLISH_LEVELS = {
    "competent": "IELTS 6 in each band, or PTE Academic L47 R48 W51 S54",
    "proficient": "IELTS 7 in each band, or PTE Academic L58 R59 W69 S76",
    "superior": "IELTS 8 in each band, or PTE Academic L69 R70 W85 S88",
}
ENGLISH_485 = "IELTS 6.5 overall with no band below 5.5 (or equivalent), from one in-centre sitting taken within 1 year before lodging"
ENGLISH_EXEMPT_PASSPORTS = {"united kingdom", "uk", "united states", "usa", "us", "canada", "new zealand", "ireland", "republic of ireland"}

POINTS_REFORM_NOTE = ("The 2026-27 Budget announced an 'optimised' points test favouring younger, higher-skilled and "
                      "higher-earning applicants. No new table or start date has been legislated, so Pathway applies the "
                      "current table. Re-check before lodging an EOI.")

# ---------------------------------------------------------------------------
# Income thresholds from 1 July 2026 (indexed 3.8%).
# ---------------------------------------------------------------------------
CSIT = 79423
SSIT = 146576
TSMIT = 79423

PLANNING_2026_27 = {"total": 185000, "employer": 58040, "189": 21090, "190": 35500, "491": 14110, "talent": 3500, "partner": 41500,
                    "previous": {"employer": 44000, "189": 16900, "190": 33000, "491": 33000, "talent": 5300, "partner": 40500}}

# ---------------------------------------------------------------------------
# Skills assessment authorities by occupation family (indicative fees).
# ---------------------------------------------------------------------------
ASSESSORS = {
    "engineering": {"name": "Engineers Australia", "url": "https://www.engineersaustralia.org.au/For-Migrants/Migration-Skills-Assessment",
                    "options": [("Australian accredited engineering degree", 346.5, "Fastest route for graduates of an EA-accredited Australian degree"),
                                ("Washington, Sydney or Dublin Accord degree", 555.5, ""),
                                ("Competency Demonstration Report (CDR)", 1034, "About 15 weeks before an assessor is assigned"),
                                ("Fast track add-on", 396, "Assigned within 20 business days")],
                    "weeks": (4, 15), "professionalYear": True},
    "ict": {"name": "Australian Computer Society", "url": "https://www.acs.org.au/msa.html",
            "options": [("Post Australian Study", 1136, "4 to 6 weeks"), ("General Skills", 1498, "4 to 6 weeks")], "weeks": (4, 6), "professionalYear": True},
    "accounting": {"name": "CPA Australia, CA ANZ or IPA", "url": "https://www.cpaaustralia.com.au/become-a-cpa/migration-assessment",
                   "options": [("Qualification assessment (onshore)", 565, "About 10 business days")], "weeks": (2, 4), "professionalYear": True},
    "nursing": {"name": "ANMAC", "url": "https://www.anmac.org.au/skilled-migration-services",
                "options": [("Modified assessment (AHPRA registered)", 395, ""), ("Full assessment", 595, "")], "weeks": (6, 16), "professionalYear": False},
    "teaching": {"name": "AITSL", "url": "https://www.aitsl.edu.au/migrate-to-australia",
                 "options": [("Skills assessment", 1154, "Most within 4 weeks")], "weeks": (4, 6), "professionalYear": False},
    "trades": {"name": "Trades Recognition Australia", "url": "https://www.tradesrecognitionaustralia.gov.au/",
               "options": [("Migration Skills Assessment", 795, "About 120 days")], "weeks": (8, 17), "professionalYear": False},
    "general": {"name": "VETASSESS", "url": "https://www.vetassess.com.au/skills-assessment-for-migration",
                "options": [("Full professional assessment (in Australia)", 1205.6, "About 7 weeks"), ("Priority add-on", 907.5, "10 business days")],
                "weeks": (2, 8), "professionalYear": False},
}

# Field of study decides which assessing authority Pathway shows. The nominated occupation
# is what the authority finally assesses, so the UI asks the person to confirm it.
FIELDS_OF_STUDY = [
    ("engineering", "Engineering", "engineering"),
    ("ict", "IT, computing or data science", "ict"),
    ("accounting", "Accounting or finance", "accounting"),
    ("nursing", "Nursing or midwifery", "nursing"),
    ("teaching", "Teaching", "teaching"),
    ("trades", "Trade qualification", "trades"),
    ("other", "Other field (business, science, arts, health...)", "general"),
]
FIELD_TO_ASSESSOR = {value: key for value, _, key in FIELDS_OF_STUDY}

APPROX_COSTS = {
    "englishTest": (410, 480, "IELTS or PTE Academic, one sitting (approximate; check the test provider)"),
    "professionalYear": (10000, 16000, "Professional Year program, about 44 weeks including an internship (approximate)"),
    "naati": (800, 900, "NAATI Credentialed Community Language test (approximate)"),
    "medical": (300, 500, "Panel physician health examination per person (approximate)"),
    "police": (50, 150, "Police certificate per country (approximate)"),
    "ovhc": (600, 1500, "Overseas Visitor Health Cover per year, single (approximate, varies by insurer)"),
}

# ---------------------------------------------------------------------------
# States and territories. Program facts change each year: show them as dated notes
# alongside the live program page excerpt.
# ---------------------------------------------------------------------------
STATES = {
    "QLD": {"name": "Queensland", "url": "https://migration.qld.gov.au/visa-options/skilled-visas/registering-your-interest-in-queenslands-migration-program",
            "graduateUrl": "https://www.migration.qld.gov.au/visa-options/skilled-visas/graduates-of-a-queensland-university",
            "status": "Not yet open for 2026-27 (2025-26 closed). Allocation not confirmed.", "allocationPrev": "1,850 / 750",
            "streams": ["Graduates of a Queensland university: bachelor, masters or PhD completed 100% in QLD after 1 July 2021; 65+ points; competent English; occupation on the QLD Onshore Skilled Occupation List.",
                        "190 graduate or onshore worker: 9 months working in QLD immediately before the ROI, at least 20 hours a week, after the qualification.",
                        "491 graduate or onshore worker: 6 months working in regional QLD immediately before the ROI, at least 20 hours a week.",
                        "Commitment: 2 years in QLD after a 190 grant; 3 years in regional QLD after a 491 grant. A 491 applicant or holder cannot later be nominated for 190 by QLD."],
            "regional": "All of Queensland except Greater Brisbane (Brisbane, Logan, Ipswich, Moreton Bay, Redland) is regional. Gold Coast and Sunshine Coast are Category 2; most other areas are Category 3.",
            "graduateMonths190": 9, "graduateMonths491": 6},
    "NSW": {"name": "New South Wales", "url": "https://www.nsw.gov.au/visas-and-migration/skilled-visas",
            "status": "Not yet open for 2026-27 at last check.", "allocationPrev": "2,100 / 1,500",
            "streams": ["190: invitation based on points and occupation demand; generally selects higher ranked EOIs.", "491: regional pathways with regional residence or employment."],
            "regional": "Sydney is not regional. Newcastle, Lake Macquarie and Wollongong are Category 2."},
    "VIC": {"name": "Victoria", "url": "https://liveinmelbourne.vic.gov.au/migrate/skilled-migration-visas",
            "status": "New ROIs closed 28 April 2026 after oversubscription; existing ROIs stay in the pool.", "allocationPrev": "2,700 / 700",
            "streams": ["Registration of Interest; no published occupation list; selection on employment, skills and occupation demand."],
            "regional": "Melbourne is not regional. Geelong is Category 2."},
    "SA": {"name": "South Australia", "url": "https://migration.sa.gov.au/",
           "status": "Reopened 26 August 2026 for 190 and 491.", "allocationPrev": "",
           "streams": ["South Australian graduates", "Skilled employment in SA", "Outer regional and offshore streams (occupation dependent)"],
           "regional": "All of South Australia, including Adelaide, is regional (Adelaide is Category 2)."},
    "WA": {"name": "Western Australia", "url": "https://migration.wa.gov.au/our-services-support/state-nominated-migration-program",
           "status": "Open; 2026-27 invitation rounds running from mid-September 2026.", "allocationPrev": "",
           "streams": ["WA graduates", "General stream from the WA skilled occupation lists", "Invitation rounds with published cut-offs"],
           "regional": "Perth is Category 2 regional."},
    "TAS": {"name": "Tasmania", "url": "https://www.migration.tas.gov.au/",
            "status": "Open; ROIs from 17 August 2026, weekly invitations. Allocation 1,250 / 800.", "allocationPrev": "",
            "streams": ["Gold and Green pass pathways for people already living and working in Tasmania", "Tasmanian graduates", "Offshore applicants need a Tasmanian job offer or study link"],
            "regional": "All of Tasmania is regional (Hobart Category 2)."},
    "ACT": {"name": "Australian Capital Territory", "url": "https://www.act.gov.au/migration",
            "status": "Open; new portal since 30 July 2026. Canberra Matrix continues.", "allocationPrev": "",
            "streams": ["Canberra residents (matrix score)", "Overseas applicants for critical skills"],
            "regional": "All of the ACT counts as regional for 491 (Category 2)."},
    "NT": {"name": "Northern Territory", "url": "https://theterritory.com.au/migrate",
           "status": "Open since 21 August 2026 for onshore and selected offshore streams. Allocation 850 / 1,000.", "allocationPrev": "",
           "streams": ["NT residents", "NT graduates", "Offshore (selected occupations)"],
           "regional": "All of the NT is Category 3 regional."},
}
STATE_STATUS_VERIFIED = "2026-10-03"

# Australian institutions recognised by the resume parser: (state, regional category).
# "check" means the institution has metropolitan and regional campuses, so the campus decides.
INSTITUTIONS = {
    "queensland university of technology": ("QLD", "no"), "qut": ("QLD", "no"), "university of queensland": ("QLD", "no"),
    "griffith university": ("QLD", "check"), "james cook university": ("QLD", "check"), "university of southern queensland": ("QLD", "check"),
    "unisq": ("QLD", "check"), "central queensland university": ("QLD", "check"), "cquniversity": ("QLD", "check"),
    "bond university": ("QLD", "cat2"), "university of the sunshine coast": ("QLD", "cat2"), "australian catholic university": ("NSW", "check"),
    "university of sydney": ("NSW", "no"), "unsw": ("NSW", "no"), "university of new south wales": ("NSW", "no"),
    "university of technology sydney": ("NSW", "no"), "macquarie university": ("NSW", "no"), "western sydney university": ("NSW", "no"),
    "university of newcastle": ("NSW", "cat2"), "university of wollongong": ("NSW", "cat2"), "charles sturt university": ("NSW", "cat3"),
    "southern cross university": ("NSW", "check"), "university of new england": ("NSW", "cat3"),
    "university of melbourne": ("VIC", "no"), "monash university": ("VIC", "no"), "rmit": ("VIC", "no"), "deakin university": ("VIC", "no"),
    "la trobe university": ("VIC", "no"), "swinburne": ("VIC", "no"), "victoria university": ("VIC", "no"), "federation university": ("VIC", "check"),
    "university of adelaide": ("SA", "cat2"), "university of south australia": ("SA", "cat2"), "adelaide university": ("SA", "cat2"), "flinders university": ("SA", "cat2"),
    "university of western australia": ("WA", "cat2"), "curtin university": ("WA", "cat2"), "murdoch university": ("WA", "cat2"),
    "edith cowan university": ("WA", "cat2"), "university of tasmania": ("TAS", "cat2"), "australian national university": ("ACT", "cat2"),
    "university of canberra": ("ACT", "cat2"), "charles darwin university": ("NT", "cat3"),
}

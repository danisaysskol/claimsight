"""Reference / master data used by the synthetic generator.

Curated Pakistani-context lookup lists plus small ICD-10-style and CPT-style
code books. Kept in one place so the generator and tests share a single source
of truth. Nothing here contains real patient information.
"""

from __future__ import annotations

# Pakistani cities the TPA operates in.
CITIES: list[str] = [
    "Karachi",
    "Lahore",
    "Islamabad",
    "Faisalabad",
    "Multan",
    "Peshawar",
    "Rawalpindi",
    "Hyderabad",
    "Quetta",
]

# Rough population weights so Karachi/Lahore dominate volume realistically.
CITY_WEIGHTS: list[float] = [0.28, 0.22, 0.10, 0.09, 0.07, 0.07, 0.07, 0.06, 0.04]

INDUSTRIES: list[str] = [
    "Textiles",
    "Banking",
    "Telecom",
    "FMCG",
    "Pharmaceuticals",
    "Cement",
    "Power & Energy",
    "IT Services",
    "Logistics",
    "Agriculture",
    "Automobile",
    "Retail",
]

# Employer group name fragments -> realistic-sounding Pakistani companies.
EMPLOYER_PREFIXES: list[str] = [
    "Habib",
    "Lucky",
    "Engro",
    "Descon",
    "Systems",
    "Packages",
    "Fauji",
    "Nishat",
    "Sapphire",
    "Interloop",
    "Gul Ahmed",
    "Service",
    "Attock",
    "Millat",
    "Bestway",
    "National",
    "Unity",
    "Meezan",
    "Askari",
    "Shahtaj",
]
EMPLOYER_SUFFIXES: list[str] = [
    "Industries",
    "Textile Mills",
    "Foods",
    "Corporation",
    "Limited",
    "Group",
    "Enterprises",
    "Pvt Ltd",
    "Holdings",
    "Pakistan",
]

# Hospital / provider name fragments.
HOSPITAL_PREFIXES: list[str] = [
    "Aga Khan",
    "Shifa",
    "Liaquat National",
    "Indus",
    "Shaukat Khanum",
    "South City",
    "Ziauddin",
    "Doctors",
    "National",
    "Fatima",
    "Al-Shifa",
    "Hameed Latif",
    "Evercare",
    "Chughtai",
    "Farooq",
    "Umair",
    "Life Line",
    "City Care",
    "Medicare",
    "Rehman",
]
HOSPITAL_TYPES_NAME: list[str] = [
    "Hospital",
    "Medical Centre",
    "Clinic",
    "Diagnostics",
    "Pharmacy",
    "Healthcare",
]

PROVIDER_TYPES: list[str] = ["Hospital", "Clinic", "Diagnostic", "Pharmacy"]
PROVIDER_TYPE_WEIGHTS: list[float] = [0.45, 0.25, 0.15, 0.15]

PLAN_TIERS: list[str] = ["Bronze", "Silver", "Gold", "Platinum"]
# Annual limit, room-rent cap, deductible, copay% by tier (PKR).
PLAN_TIER_PARAMS: dict[str, dict[str, float]] = {
    "Bronze": {"annual_limit": 300_000, "room_rent_cap": 6_000, "deductible": 5_000, "copay_pct": 0.20},
    "Silver": {"annual_limit": 600_000, "room_rent_cap": 12_000, "deductible": 3_000, "copay_pct": 0.15},
    "Gold": {"annual_limit": 1_200_000, "room_rent_cap": 25_000, "deductible": 1_000, "copay_pct": 0.10},
    "Platinum": {"annual_limit": 3_000_000, "room_rent_cap": 50_000, "deductible": 0, "copay_pct": 0.05},
}
# Higher tiers approve a larger share on average.
PLAN_TIER_APPROVAL_BASE: dict[str, float] = {
    "Bronze": 0.72,
    "Silver": 0.80,
    "Gold": 0.87,
    "Platinum": 0.92,
}

CLAIM_TYPES: list[str] = [
    "Inpatient",
    "Outpatient",
    "Daycare",
    "Pharmacy",
    "Diagnostic",
    "Maternity",
    "Emergency",
]
CLAIM_TYPE_WEIGHTS: list[float] = [0.14, 0.34, 0.08, 0.18, 0.14, 0.06, 0.06]

# Base denial-rate by claim type (before provider/other effects).
CLAIM_TYPE_DENIAL_BASE: dict[str, float] = {
    "Inpatient": 0.08,
    "Outpatient": 0.12,
    "Daycare": 0.10,
    "Pharmacy": 0.06,
    "Diagnostic": 0.15,
    "Maternity": 0.05,
    "Emergency": 0.09,
}

CLAIM_STATUSES: list[str] = ["Paid", "Denied", "Pending", "Partially Paid", "In Review"]

DENIAL_REASON_CODES: dict[str, str] = {
    "DR01": "Service not covered under plan",
    "DR02": "Pre-existing condition within waiting period",
    "DR03": "Missing or invalid documentation",
    "DR04": "Non-network provider without authorisation",
    "DR05": "Annual limit exhausted",
    "DR06": "Duplicate claim",
    "DR07": "Policy not active on service date",
    "DR08": "Procedure not medically necessary",
    "DR09": "Room rent exceeds entitlement",
    "DR10": "Late submission beyond filing limit",
}

RELATIONSHIPS: list[str] = ["Self", "Spouse", "Child"]
RELATIONSHIP_WEIGHTS: list[float] = [0.45, 0.25, 0.30]

GENDERS: list[str] = ["Male", "Female"]

NETWORK_STATUSES: list[str] = ["In-Network", "Out-of-Network"]
PROVIDER_TIERS: list[str] = ["A", "B", "C"]
ADJUDICATION_MODES: list[str] = ["Auto", "Manual"]

# --- ICD-10-style diagnosis code book (code, description, chapter) ---
DIAGNOSES: list[tuple[str, str, str]] = [
    ("J06.9", "Acute upper respiratory infection", "Respiratory"),
    ("J18.9", "Pneumonia, unspecified organism", "Respiratory"),
    ("J45.9", "Asthma, unspecified", "Respiratory"),
    ("J20.9", "Acute bronchitis", "Respiratory"),
    ("J44.9", "Chronic obstructive pulmonary disease", "Respiratory"),
    ("A09", "Infectious gastroenteritis and colitis", "Digestive"),
    ("K35.80", "Acute appendicitis", "Digestive"),
    ("K21.9", "Gastro-oesophageal reflux disease", "Digestive"),
    ("K80.20", "Calculus of gallbladder", "Digestive"),
    ("E11.9", "Type 2 diabetes mellitus", "Endocrine"),
    ("E78.5", "Hyperlipidaemia, unspecified", "Endocrine"),
    ("E03.9", "Hypothyroidism, unspecified", "Endocrine"),
    ("I10", "Essential (primary) hypertension", "Circulatory"),
    ("I25.10", "Atherosclerotic heart disease", "Circulatory"),
    ("I50.9", "Heart failure, unspecified", "Circulatory"),
    ("I63.9", "Cerebral infarction, unspecified", "Circulatory"),
    ("N39.0", "Urinary tract infection", "Genitourinary"),
    ("N18.9", "Chronic kidney disease, unspecified", "Genitourinary"),
    ("O80", "Normal delivery", "Pregnancy"),
    ("O82", "Caesarean delivery", "Pregnancy"),
    ("O21.9", "Vomiting of pregnancy, unspecified", "Pregnancy"),
    ("S72.0", "Fracture of neck of femur", "Injury"),
    ("S52.5", "Fracture of lower end of radius", "Injury"),
    ("T14.90", "Injury, unspecified", "Injury"),
    ("B54", "Unspecified malaria", "Infectious"),
    ("A90", "Dengue fever", "Infectious"),
    ("A01.0", "Typhoid fever", "Infectious"),
    ("B18.2", "Chronic viral hepatitis C", "Infectious"),
    ("C50.9", "Malignant neoplasm of breast", "Neoplasm"),
    ("C34.90", "Malignant neoplasm of lung", "Neoplasm"),
    ("D64.9", "Anaemia, unspecified", "Blood"),
    ("M54.5", "Low back pain", "Musculoskeletal"),
    ("M17.9", "Osteoarthritis of knee", "Musculoskeletal"),
    ("H25.9", "Age-related cataract", "Eye"),
    ("H66.9", "Otitis media, unspecified", "Ear"),
    ("F32.9", "Major depressive disorder, single episode", "Mental"),
    ("R51", "Headache", "Symptoms"),
    ("R10.9", "Abdominal pain, unspecified", "Symptoms"),
    ("Z34.9", "Supervision of normal pregnancy", "Pregnancy"),
    ("Z00.0", "General adult medical examination", "Wellness"),
]

# Diagnosis chapters that spike in winter (respiratory season).
WINTER_CHAPTERS: set[str] = {"Respiratory"}

# --- CPT-style procedure code book (code, description, category, typical_cost_pkr) ---
PROCEDURES: list[tuple[str, str, str, int]] = [
    ("99213", "Outpatient consultation, established patient", "Consultation", 2_500),
    ("99204", "Outpatient consultation, new patient", "Consultation", 4_000),
    ("99284", "Emergency department visit, moderate", "Emergency", 8_000),
    ("99223", "Inpatient care, initial, high complexity", "Inpatient", 15_000),
    ("80053", "Comprehensive metabolic panel", "Laboratory", 1_800),
    ("85025", "Complete blood count with differential", "Laboratory", 900),
    ("80061", "Lipid panel", "Laboratory", 1_500),
    ("83036", "Haemoglobin A1c", "Laboratory", 1_200),
    ("87804", "Rapid influenza test", "Laboratory", 2_000),
    ("71046", "Chest X-ray, two views", "Radiology", 2_500),
    ("74177", "CT abdomen and pelvis with contrast", "Radiology", 22_000),
    ("70551", "MRI brain without contrast", "Radiology", 28_000),
    ("76700", "Ultrasound, abdomen complete", "Radiology", 4_500),
    ("93000", "Electrocardiogram, complete", "Cardiology", 2_200),
    ("93306", "Echocardiography, complete", "Cardiology", 9_000),
    ("45378", "Colonoscopy, diagnostic", "Surgery", 35_000),
    ("47562", "Laparoscopic cholecystectomy", "Surgery", 180_000),
    ("44970", "Laparoscopic appendectomy", "Surgery", 145_000),
    ("59400", "Routine obstetric care, vaginal delivery", "Maternity", 90_000),
    ("59510", "Routine obstetric care, caesarean delivery", "Maternity", 160_000),
    ("27447", "Total knee arthroplasty", "Surgery", 650_000),
    ("27130", "Total hip arthroplasty", "Surgery", 720_000),
    ("66984", "Cataract removal with lens insertion", "Surgery", 75_000),
    ("36415", "Routine venipuncture", "Laboratory", 300),
    ("90471", "Immunisation administration", "Preventive", 1_500),
    ("99396", "Preventive visit, established patient", "Preventive", 3_500),
    ("J1885", "Ketorolac injection", "Pharmacy", 600),
    ("J0696", "Ceftriaxone injection", "Pharmacy", 1_100),
    ("RX100", "Antibiotic course (oral)", "Pharmacy", 1_800),
    ("RX200", "Antihypertensive (monthly)", "Pharmacy", 2_400),
    ("RX300", "Antidiabetic (monthly)", "Pharmacy", 3_000),
    ("RX400", "Inhaler / bronchodilator", "Pharmacy", 2_800),
]

# Map claim types to the procedure categories that plausibly occur under them.
CLAIM_TYPE_TO_PROC_CATEGORIES: dict[str, list[str]] = {
    "Inpatient": ["Inpatient", "Surgery", "Radiology", "Laboratory", "Cardiology"],
    "Outpatient": ["Consultation", "Laboratory", "Preventive", "Cardiology"],
    "Daycare": ["Surgery", "Radiology", "Laboratory"],
    "Pharmacy": ["Pharmacy"],
    "Diagnostic": ["Laboratory", "Radiology", "Cardiology"],
    "Maternity": ["Maternity", "Laboratory", "Radiology", "Consultation"],
    "Emergency": ["Emergency", "Radiology", "Laboratory"],
}

# Map claim types to plausible diagnosis chapters.
CLAIM_TYPE_TO_DIAG_CHAPTERS: dict[str, list[str]] = {
    "Inpatient": ["Circulatory", "Digestive", "Respiratory", "Injury", "Neoplasm", "Genitourinary"],
    "Outpatient": ["Endocrine", "Circulatory", "Symptoms", "Musculoskeletal", "Wellness", "Respiratory"],
    "Daycare": ["Digestive", "Eye", "Genitourinary", "Musculoskeletal"],
    "Pharmacy": ["Endocrine", "Circulatory", "Respiratory", "Infectious"],
    "Diagnostic": ["Circulatory", "Endocrine", "Symptoms", "Neoplasm", "Blood"],
    "Maternity": ["Pregnancy"],
    "Emergency": ["Injury", "Respiratory", "Infectious", "Symptoms", "Digestive"],
}

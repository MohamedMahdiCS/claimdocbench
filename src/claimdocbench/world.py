"""The synthetic world a split is generated in: people, clinics, items and diagnoses.

Everything here is invented. Clinic names are combinations of generic words; any
resemblance to a real clinic is coincidental. Registration numbers use a REG-MY / REG-SG
format that does not match any real regulator's format.
"""

from __future__ import annotations

import random
from dataclasses import dataclass
from datetime import date, timedelta
from decimal import Decimal

from claimdocbench.domain import (
    Clinic,
    CoveredPerson,
    Currency,
    ItemCategory,
    Member,
    Relationship,
    VisitType,
)

# --- Names -------------------------------------------------------------------------------

MALAY_MALE = ["Ahmad", "Muhammad Hafiz", "Amirul", "Faizal", "Hakim", "Syafiq", "Azlan", "Iskandar"]
MALAY_FEMALE = ["Nur Aisyah", "Siti Hajar", "Nurul Huda", "Farah", "Aina", "Zulaikha", "Hidayah"]
MALAY_FATHER = ["Hassan", "Ismail", "Abdullah", "Rahman", "Yusof", "Osman", "Kamarudin", "Salleh"]
CHINESE_SURNAME = ["Tan", "Lim", "Lee", "Wong", "Ng", "Chong", "Goh", "Teo", "Chan", "Ong"]
CHINESE_GIVEN = ["Wei Ming", "Mei Ling", "Jia Hui", "Kok Leong", "Siew Lan", "Zhi Hao", "Xin Yi"]
INDIAN_MALE = ["Arjun", "Suresh", "Ganesh", "Vikram", "Rajesh", "Kumar"]
INDIAN_FEMALE = ["Priya", "Kavitha", "Deepa", "Anitha", "Shalini", "Meena"]
INDIAN_FATHER = ["Raman", "Muthu", "Krishnan", "Subramaniam", "Gopal", "Nair"]
OTHER_GIVEN = ["Daniel", "Sarah", "Michael", "Grace", "Ryan", "Joanne", "Marcus", "Natalie"]
OTHER_SURNAME = ["Fernandez", "D'Cruz", "Pereira", "Lopez", "Wright", "Santos"]


@dataclass(frozen=True)
class PersonName:
    full_name: str
    origin: str  # malay | chinese | indian | other  (used for fairness slices)


def random_name(rng: random.Random, origin: str | None = None) -> PersonName:
    origin = origin or rng.choice(["malay", "malay", "chinese", "chinese", "indian", "other"])
    female = rng.random() < 0.5
    if origin == "malay":
        given = rng.choice(MALAY_FEMALE if female else MALAY_MALE)
        link = "binti" if female else "bin"
        return PersonName(f"{given} {link} {rng.choice(MALAY_FATHER)}", origin)
    if origin == "chinese":
        return PersonName(f"{rng.choice(CHINESE_SURNAME)} {rng.choice(CHINESE_GIVEN)}", origin)
    if origin == "indian":
        given = rng.choice(INDIAN_FEMALE if female else INDIAN_MALE)
        link = "a/p" if female else "a/l"
        return PersonName(f"{given} {link} {rng.choice(INDIAN_FATHER)}", origin)
    return PersonName(f"{rng.choice(OTHER_GIVEN)} {rng.choice(OTHER_SURNAME)}", "other")


# --- Clinics -----------------------------------------------------------------------------

MY_GP_PREFIX = ["Klinik", "Poliklinik", "Klinik Keluarga"]
SG_GP_PREFIX = ["", "Family", "Medical"]
CLINIC_WORDS = [
    "Seri Murni",
    "Cahaya",
    "Harmoni",
    "Bayu",
    "Mutiara",
    "Sentosa",
    "Delima",
    "Lakeside",
    "Maple",
    "Riverside",
    "Greenfield",
    "Orchid",
    "Sunrise",
    "Kenanga",
]
SPECIALTIES = ["ENT", "Dermatology", "Orthopaedic", "Paediatric", "Gastro", "Eye"]
MY_TOWNS = [
    "Petaling Jaya",
    "Shah Alam",
    "Johor Bahru",
    "Georgetown",
    "Ipoh",
    "Kuching",
    "Kota Kinabalu",
    "Seremban",
    "Melaka",
    "Kuantan",
]
SG_AREAS = ["Tampines", "Jurong East", "Bishan", "Woodlands", "Toa Payoh", "Bedok", "Clementi"]


@dataclass(frozen=True)
class ClinicProfile:
    clinic: Clinic
    country: str  # MY | SG
    address: str
    phone: str
    receipt_prefix: str
    doctors: tuple[str, ...]


def _clinic_profile(
    rng: random.Random, country: str, kind: VisitType, n: int, licensed: bool = True
) -> ClinicProfile:
    word = rng.choice(CLINIC_WORDS)
    if kind is VisitType.SPECIALIST:
        name = f"{word} {rng.choice(SPECIALTIES)} Specialist Centre"
    elif country == "MY":
        name = f"{rng.choice(MY_GP_PREFIX)} {word}"
    else:
        name = f"{word} {rng.choice(SG_GP_PREFIX)} Clinic".replace("  ", " ")
    if country == "MY":
        address = (
            f"No. {rng.randint(1, 120)}, Jalan {rng.choice(CLINIC_WORDS)} {rng.randint(1, 9)}, "
            f"{rng.randint(10000, 98000)} {rng.choice(MY_TOWNS)}"
        )
        phone = f"0{rng.randint(3, 9)}-{rng.randint(1000, 9999)} {rng.randint(1000, 9999)}"
    else:
        address = (
            f"Blk {rng.randint(100, 900)} {rng.choice(SG_AREAS)} St {rng.randint(1, 90)}, "
            f"#01-{rng.randint(10, 99)}, Singapore {rng.randint(100000, 799999)}"
        )
        phone = f"6{rng.randint(100, 999)} {rng.randint(1000, 9999)}"
    initials = "".join(w[0] for w in name.split() if w[0].isalpha())[:3].upper()
    clinic_id = f"{country}-{'SP' if kind is VisitType.SPECIALIST else 'GP'}-{n:04d}"
    return ClinicProfile(
        clinic=Clinic(
            clinic_id=clinic_id,
            name=name,
            registration_no=f"REG-{country}-{rng.randint(10000, 99999)}",
            kind=kind,
            licensed=licensed,
        ),
        country=country,
        address=address,
        phone=phone,
        receipt_prefix=f"{initials}{rng.randint(1, 9)}",
        doctors=tuple(f"Dr. {random_name(rng).full_name}" for _ in range(rng.randint(1, 3))),
    )


# --- Items and diagnoses -----------------------------------------------------------------

# (description, min amount, max amount) per category, in the schedule currency.
CATALOG: dict[ItemCategory, list[tuple[str, int, int]]] = {
    ItemCategory.CONSULTATION: [("Consultation fee", 25, 60), ("Doctor consultation", 30, 70)],
    ItemCategory.MEDICATION: [
        ("Paracetamol 500mg x 10", 3, 8),
        ("Amoxicillin 500mg x 15", 12, 25),
        ("Loratadine 10mg x 10", 8, 15),
        ("Cough syrup 100ml", 9, 18),
        ("Omeprazole 20mg x 14", 15, 30),
        ("Ibuprofen 400mg x 10", 5, 12),
        ("Salbutamol inhaler", 18, 35),
        ("Metformin 500mg x 30", 10, 22),
    ],
    ItemCategory.PROCEDURE: [
        ("Wound dressing", 15, 40),
        ("Nebuliser treatment", 20, 45),
        ("Ear irrigation", 25, 60),
        ("Minor suturing", 60, 150),
    ],
    ItemCategory.LAB_TEST: [
        ("Full blood count", 20, 45),
        ("Urine FEME", 10, 25),
        ("HbA1c test", 30, 60),
        ("Lipid profile", 35, 70),
    ],
    ItemCategory.SUPPLEMENT: [
        ("Vitamin C 1000mg x 30", 20, 45),
        ("Multivitamin tablets x 30", 25, 60),
        ("Fish oil capsules x 60", 30, 75),
        ("Herbal tonic 500ml", 15, 40),
    ],
    ItemCategory.COSMETIC: [
        ("Acne laser session", 120, 350),
        ("Skin whitening cream", 40, 120),
        ("Chemical peel", 100, 250),
    ],
    ItemCategory.FERTILITY: [
        ("Fertility consultation", 80, 200),
        ("Ovulation induction", 150, 400),
    ],
    ItemCategory.DENTAL: [
        ("Scaling and polishing", 60, 150),
        ("Tooth filling", 80, 180),
        ("Dental X-ray", 30, 70),
    ],
    ItemCategory.HEALTH_SCREENING: [
        ("Health screening package", 120, 400),
        ("Annual medical check-up", 100, 300),
    ],
}

SPECIALIST_CONSULTATION = ("Specialist consultation", 120, 300)

ACUTE_DIAGNOSES = {
    "J06.9": "Acute upper respiratory infection",
    "A09": "Acute gastroenteritis",
    "J02.9": "Acute pharyngitis",
    "M54.5": "Low back pain",
    "L30.9": "Dermatitis",
    "H10.9": "Conjunctivitis",
    "R50.9": "Fever",
}
CHRONIC_DIAGNOSES = {
    "E11.9": "Type 2 diabetes mellitus",
    "I10": "Essential hypertension",
    "J45.9": "Asthma",
    "E78.5": "Hyperlipidaemia",
}
DIAGNOSES = ACUTE_DIAGNOSES | CHRONIC_DIAGNOSES


def money(rng: random.Random, low: int, high: int) -> Decimal:
    """A price that looks like a clinic price: whole ringgit/dollars or .50 most of the time."""
    whole = rng.randint(low, high)
    cents = rng.choice([0, 0, 0, 50, 50, rng.randint(1, 99)])
    return Decimal(f"{whole}.{cents:02d}")


# --- Members -----------------------------------------------------------------------------

EMPLOYERS_MY = ["Synthetica Sdn Bhd", "Orbitron Logistics Sdn Bhd", "Kenari Digital Sdn Bhd"]
EMPLOYERS_SG = ["Synthetica Pte Ltd", "Harbourline Analytics Pte Ltd", "Pinewood Labs Pte Ltd"]


@dataclass(frozen=True)
class MemberProfile:
    member: Member
    country: str
    employer: str
    names: dict[str, PersonName]  # person_id -> name (with origin)


def _member(rng: random.Random, n: int, country: str) -> MemberProfile:
    plan_id = rng.choice(["A", "B"])
    currency = Currency.MYR if country == "MY" else Currency.SGD
    # Most members are covered for calendar 2026; some joined mid-year (for waiting periods).
    if rng.random() < 0.75:
        start = date(2026, 1, 1)
    else:
        start = date(2026, 1, 1) + timedelta(days=rng.randint(30, 200))
    end = start + timedelta(days=364)
    self_name = random_name(rng)
    persons = [
        CoveredPerson(
            person_id=f"P{n:05d}-0",
            full_name=self_name.full_name,
            relationship=Relationship.SELF,
            preexisting_conditions=frozenset(
                rng.sample(sorted(CHRONIC_DIAGNOSES), k=rng.choice([0, 0, 1]))
            ),
        )
    ]
    names = {persons[0].person_id: self_name}
    for k, rel in enumerate(
        rng.sample(
            [Relationship.SPOUSE, Relationship.CHILD, Relationship.CHILD], k=rng.randint(0, 2)
        ),
        start=1,
    ):
        name = random_name(rng, self_name.origin)
        person = CoveredPerson(
            person_id=f"P{n:05d}-{k}",
            full_name=name.full_name,
            relationship=rel,
            covered=rng.random() < 0.8,
        )
        persons.append(person)
        names[person.person_id] = name
    member = Member(
        member_id=f"GHS-{country}-{n:05d}",
        plan_id=plan_id,
        currency=currency,
        coverage_start=start,
        coverage_end=end,
        persons=tuple(persons),
    )
    employer = rng.choice(EMPLOYERS_MY if country == "MY" else EMPLOYERS_SG)
    return MemberProfile(member, country, employer, names)


# --- The world ---------------------------------------------------------------------------


@dataclass
class World:
    members: list[MemberProfile]
    clinics: dict[str, ClinicProfile]

    @property
    def registry(self) -> dict[str, Clinic]:
        """The insurer's clinic registry (what a system can look up)."""
        return {cid: p.clinic for cid, p in self.clinics.items()}

    def clinics_for(
        self, country: str, kind: VisitType, licensed: bool = True
    ) -> list[ClinicProfile]:
        return [
            p
            for p in self.clinics.values()
            if p.country == country and p.clinic.kind is kind and p.clinic.licensed == licensed
        ]


def build_world(rng: random.Random, n_members: int) -> World:
    clinics: dict[str, ClinicProfile] = {}
    counter = 0
    for country in ("MY", "SG"):
        for kind, count in ((VisitType.GP, 12), (VisitType.SPECIALIST, 5)):
            for _ in range(count):
                counter += 1
                p = _clinic_profile(rng, country, kind, counter)
                clinics[p.clinic.clinic_id] = p
        for _ in range(2):  # listed in the registry but not licensed
            counter += 1
            p = _clinic_profile(rng, country, VisitType.GP, counter, licensed=False)
            clinics[p.clinic.clinic_id] = p
    members = [_member(rng, i, rng.choice(["MY", "MY", "SG"])) for i in range(1, n_members + 1)]
    return World(members=members, clinics=clinics)


def fabricated_clinic(rng: random.Random, country: str) -> ClinicProfile:
    """A clinic that is not in the registry (used for UNKNOWN_CLINIC fraud)."""
    p = _clinic_profile(rng, country, VisitType.GP, 9000 + rng.randint(0, 999))
    return ClinicProfile(
        clinic=p.clinic.model_copy(update={"clinic_id": "UNREGISTERED"}),
        country=country,
        address=p.address,
        phone=p.phone,
        receipt_prefix=p.receipt_prefix,
        doctors=p.doctors,
    )

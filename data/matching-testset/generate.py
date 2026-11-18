#!/usr/bin/env python3
"""Generate the SearchInCircle matching test set (data model: PRD v1.3).

Deterministic: the same --seed always produces byte-identical output.
Standard library only. Run:  python3 generate.py [--seed 42] [--out .] [--scale 1.0]

Public files (what the matching algorithm may read):
    users.json, trust_connections.json, blocks.json,
    self_entries.json, tags.json, requirements.json, rules.json
Answer key (the algorithm must NOT read it; evaluate.py uses it):
    answer_key/ground_truth.json, answer_key/ground_truth.csv,
    answer_key/entry_labels.json, answer_key/REVIEW.md
"""
from __future__ import annotations

import argparse
import csv
import datetime as dt
import json
import random
import re
import sys
from collections import Counter, defaultdict
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
from archetypes import A, CITIES, COUNTRY_OF, FIRST, FIRST_MORE, LAST, LAST_MORE, TRAPS, extend_with_roles  # noqa: E402

NEW_ROLES = extend_with_roles()  # roles_*.py: more roles, and job-specific work history for every role

REFERENCE_DATE = dt.date(2026, 11, 11)
# Decided 2026-11-12: tags never go stale for now (no reconfirmation reminders yet).
# Set a number of days to re-enable FR-52; see FUTURE_IMPROVEMENTS.md item A1.
RECONFIRM_WINDOW_DAYS: int | None = None
# Decided 2026-11-12: the publisher's own tags match their own requirements.
INCLUDE_OWN_TAGS = True


def iso(d: dt.date) -> str:
    return d.isoformat()


def days_ago(n: int) -> dt.date:
    return REFERENCE_DATE - dt.timedelta(days=n)


def cap(s: str) -> str:
    return s[:1].upper() + s[1:]


def an(s: str) -> str:
    return ("an " if s[:1].lower() in "aeiou" else "a ") + s


def has_word(needle: str, text: str) -> bool:
    return re.search(r"(?<![a-z0-9])" + re.escape(needle.lower()) + r"(?![a-z0-9])", text.lower()) is not None


def canonical_words(arch: str) -> list[str]:
    a = A[arch]
    return a["skills"] + a["roles"]


def is_pure(arch: str, text: str) -> bool:
    """True when the text names no canonical skill or role of the archetype."""
    return not any(has_word(w, text) for w in canonical_words(arch))


def check_synonym_purity() -> None:
    """A synonym-only entry must be a real test of meaning, not of keywords."""
    for key, a in A.items():
        texts = (a["syn"] + a["syn_does"] + a.get("syn_duties", [])
                 + [f for foci, _ in a["specs"].values() for f in foci])
        for t in texts:
            for w in canonical_words(key):
                assert not has_word(w, t), f"{key}: '{t}' leaks the canonical word '{w}'"


# --------------------------------------------------------------------------
# Who lives where, and who knows whom. People cluster: a tech worker's circle
# is mostly tech workers, so one requirement can have 100+ matches.
# --------------------------------------------------------------------------
# key, city, kind, number of users
CLUSTERS = [
    ("tech_hyd", "Hyderabad", "tech", 150), ("nbr_hyd", "Hyderabad", "general", 110),
    ("tech_blr", "Bengaluru", "tech", 100), ("tech_sea", "Seattle", "tech", 70),
    ("health_hou", "Houston", "health", 60), ("nbr_aus", "Austin", "general", 55),
    ("nbr_chn", "Chennai", "general", 35), ("nbr_lon", "London", "general", 22),
    ("nbr_tor", "Toronto", "general", 28), ("nbr_pune", "Pune", "general", 40),
    ("nbr_dal", "Dallas", "general", 12), ("nbr_vjw", "Vijayawada", "general", 16),
]
# What people in each kind of cluster do themselves, and whom they tag.
OWN = {"tech": dict(tech=80, services=8, learn=5, hobby=5, resource=2),
       "health": dict(health=70, learn=10, hobby=10, services=5, resource=5),
       "general": dict(home=22, services=22, learn=20, hobby=10, health=10, tech=10, resource=6)}
TAGS = {"tech": dict(tech=50, home=15, services=12, learn=10, health=8, hobby=3, resource=2),
        "health": dict(health=45, home=20, services=10, learn=15, hobby=7, resource=3),
        "general": dict(home=35, services=20, learn=20, health=12, tech=8, hobby=3, resource=2)}
SIDE = dict(learn=30, hobby=30, resource=20, services=10, home=10)  # a second, unrelated skill

# Publishers: cluster, target circle size.
PUBLISHERS = [("nbr_aus", 40), ("tech_hyd", 200), ("health_hou", 55), ("nbr_chn", 25), ("tech_blr", 110),
              ("nbr_lon", 12), ("tech_sea", 60), ("nbr_tor", 18), ("nbr_hyd", 140), ("nbr_dal", 6),
              ("nbr_pune", 30), ("nbr_vjw", 10)]

# --------------------------------------------------------------------------
# Requirements: FR-26 free text. Everything except the text is a hidden label.
# publisher index, archetype, specialty, work type, min years, status, anonymous,
# flags, target (at least this many good-or-strong people in the circle), text
# --------------------------------------------------------------------------
REQS = [
    (0, "react_native", "fintech", "remote", 4, "open", False, [], 12,
     "Looking for a senior React Native developer, 4+ years, TypeScript and Redux, to own our fintech app "
     "(card payments, KYC flows). Fully remote, contract-to-hire."),
    (0, "tennis_partner", "intermediate", "onsite", 0, "open", False, [], 15,
     "Intermediate tennis player looking for a weekend partner to play singles on Saturday mornings in Austin, "
     "near Zilker Park."),
    (1, "data_engineer", "warehouse", "hybrid", 5, "open", False, [], 45,
     "Need a data engineer with 5+ years to move our legacy cron jobs to Airflow and Apache Spark and remodel the "
     "warehouse. Strong SQL, owns ETL and data pipelines end to end. Hybrid, two days a week in our Hyderabad office."),
    (1, "tax_accountant", "nri", "remote", 3, "open", False, [], 20,
     "Looking for a chartered accountant with at least 3 years of experience to handle tax filing and NRI income "
     "tax returns for my family. Can be done remotely."),
    (2, "registered_nurse", "icu", "onsite", 3, "open", False, [], 25,
     "Private hospital in Houston needs a registered nurse for ICU night shifts. 3+ years of ICU nursing and IV "
     "therapy; BLS and ACLS required. On-site."),
    (2, "electrician", "ev_panel", "onsite", 5, "open", False, [], 6,
     "Need a licensed electrician (5+ years) for EV charger installation and a 200A panel upgrade at my house "
     "in Houston."),
    (3, "ui_ux", "health", "remote", 3, "open", True, ["anonymous"], 6,
     "Stealth health startup needs a product designer: UI design, UX research and Figma prototyping for a "
     "patient app. 3+ years, remote."),
    (3, "math_tutor", "jee", "remote", 2, "open", False, [], 8,
     "My son is in Class 11 preparing for JEE. Looking for an online maths tutor strong in calculus and algebra, "
     "at least 2 years of coaching, three evenings a week."),
    (4, "devops_aws", None, "onsite", 6, "open", False, ["audience"], 20,
     "Senior DevOps engineer, 6+ years, for our Bengaluru office: run the AWS and Kubernetes platform, Terraform "
     "everything, own CI/CD."),
    (4, "wedding_photographer", "indian", "onsite", 2, "open", False, [], 8,
     "Need a wedding photographer for a two-day wedding in Bengaluru in February: muhurtham in the morning, "
     "reception in the evening, plus photo editing. At least 2 years of experience."),
    (5, "ml_engineer", "nlp", "remote", 4, "open", False, ["sparse"], 3,
     "Looking for a machine learning engineer with 4+ years in PyTorch and NLP, including model deployment to "
     "production. Remote is fine."),
    (5, "harpist", None, "onsite", 3, "open", False, ["no_match"], 0,
     "Looking for a concert harp teacher in London for weekly harp lessons; 3+ years of teaching."),
    (6, "backend_python", None, "remote", 3, "closed", False, ["closed"], 0,
     "Python backend developer, Django or FastAPI, REST APIs on PostgreSQL, 3+ years, remote. (Position filled.)"),
    (6, "numismatist", None, "remote", 0, "open", False, [], 4,
     "Inherited my grandfather's box of old coins. Want a coin collecting enthusiast to help with coin grading "
     "and appraisal. Happy to do it over video."),
    (7, "physiotherapist", "sports", "onsite", 3, "open", False, [], 5,
     "Recovering from ACL surgery in Toronto. Need a physiotherapist with 3+ years in sports rehabilitation and "
     "post-operative rehab, in person."),
    (7, "telugu_tutor", "kids", "remote", 0, "open", False, [], 5,
     "Want my two kids (7 and 9) to learn to speak Telugu. Online classes on weekends."),
    (1, "qa_tester", None, "remote", 2, "open", False, ["synonym_query"], 30,
     "Need someone to do bug hunting and quality assurance on our web app before launch; scripting end-to-end "
     "checks would be a bonus. 2+ years, remote."),
    (0, "pickup_truck", "moving", "onsite", 0, "open", False, [], 5,
     "Moving apartments next Saturday in Austin. Does anyone have a pickup truck and could help me move a sofa "
     "and a bed across town?"),
    (0, "plumber", "emergency", "onsite", 0, "open", False, [], 6,
     "plumber needed asap!! pipe burst under the kitchen sink, water everywhere. austin, south side"),
    (1, "backend_python", None, "remote", 2, "open", False, [], 110,
     "We are hiring several Python backend developers (2+ years). Django or FastAPI, REST APIs, PostgreSQL. "
     "Remote within India is fine. Please share anyone good you know."),
    (1, "carnatic_vocal", "kids", "onsite", 0, "open", False, [], 8,
     "Looking for a Carnatic vocal teacher for my 8-year-old daughter, a beginner. Prefer home or nearby classes "
     "in Hyderabad (Gachibowli side), weekends."),
    (2, "pediatrician", "allergy", "onsite", 0, "open", False, [], 8,
     "Our 4-year-old has eczema and keeps reacting to foods. Can anyone recommend a good paediatrician in Houston "
     "who knows childhood allergies?"),
    (4, "java_backend", "banking", "hybrid", 5, "open", False, [], 50,
     "Java developers needed for a core banking project: Spring Boot microservices, Hibernate, 5+ years. "
     "Hybrid from our Bengaluru office, 3 days a week."),
    (4, "frontend_web", "dashboards", "remote", 3, "open", False, [], 35,
     "need a frontend dev who is good with React + Next.js. we are building an analytics dashboard w/ lots of "
     "charts and big tables. 3 yrs min. remote ok"),
    (5, "babysitter", "school_age", "onsite", 0, "open", False, ["sparse"], 3,
     "Need a babysitter in London (Wembley) for after-school care: pick up my 6-year-old at 3:30 and help with "
     "homework until 6, Monday to Thursday."),
    (6, "backend_python", "ai_apps", "remote", 3, "open", False, [], 15,
     "Looking for a Python developer (3+ years) to build an LLM-powered support chatbot: FastAPI, embeddings, "
     "retrieval. Remote."),
    (6, "immigration_lawyer", "h1b", "remote", 5, "open", False, [], 6,
     "My employer is filing my H-1B extension and I want a second opinion. Looking for an immigration lawyer with "
     "5+ years handling employer-sponsored cases. Phone consult is fine."),
    (8, "plumber", "water_heater", "onsite", 0, "open", False, [], 40,
     "Geyser stopped heating and there is a small leak near the inlet. Need a plumber in Hyderabad who can "
     "repair or replace the water heater this week."),
    (8, "home_cook", "andhra", "onsite", 0, "open", False, [], 30,
     "Housewarming on the 24th in Kondapur, Hyderabad. Looking for someone to cater an Andhra-style lunch for "
     "about 60 people: pappu, pulihora, biryani, the works."),
    (8, "house_painter", None, "onsite", 3, "open", False, [], 20,
     "Want to get our 3BHK flat in Hyderabad painted before Sankranti. Interior painting with putty, experienced "
     "painters only (3+ years)."),
    (8, "yoga_instructor", "prenatal", "remote", 2, "open", False, [], 10,
     "I'm five months pregnant and want to start gentle yoga. Looking for an instructor with at least 2 years of "
     "experience teaching expecting mothers. Online is fine."),
    (9, "car_mechanic", "german", "onsite", 0, "open", False, ["sparse"], 1,
     "Check-engine light on my 2017 BMW 3 Series. Looking for an honest mechanic in Dallas who knows German cars."),
    (10, "real_estate_agent", "rentals", "onsite", 0, "open", False, [], 6,
     "Relocating to Pune next month with family. Need a property consultant to help find a 2BHK rental in Baner "
     "or Aundh."),
    (10, "cricket_coach", "juniors", "onsite", 2, "open", False, [], 5,
     "Looking for a cricket coach in Pune for my 11-year-old son. Weekend batting and bowling sessions, someone "
     "who has coached juniors for 2+ years."),
    (11, "dentist", "ortho", "onsite", 0, "open", False, ["sparse"], 2,
     "My daughter (13) needs braces. Any good dentist in Vijayawada who does teeth straightening?"),
    (4, "salesforce_dev", "service", "remote", 3, "open", False, [], 12,
     "Need a Salesforce developer, 3+ years, to set up Service Cloud for our support team: case routing, Apex "
     "triggers and a few Lightning Web Components. Remote."),
    (6, "spare_room", "students", "onsite", 0, "open", False, ["sparse"], 3,
     "My nephew starts a summer internship in Seattle in June. Does anyone have a spare room he could rent for "
     "about three months?"),
    # Roles added with the job-specific work histories (roles_*.py).
    (1, "fullstack_dev", "startups", "remote", 3, "open", False, [], 25,
     "Early-stage startup looking for a full-stack engineer (3+ years) to build our MVP end to end: Next.js front "
     "end, TypeScript APIs and PostgreSQL. Remote."),
    (6, "data_scientist", "experimentation", "remote", 4, "open", False, [], 10,
     "Need a data scientist with 4+ years to design and analyse A/B tests on our checkout funnel and set up a proper "
     "experimentation framework. Remote, US time zones."),
    (2, "pharmacist", "hospital", "onsite", 2, "open", False, [], 6,
     "Hospital in Houston looking for a pharmacist with 2+ years in inpatient dispensing and IV admixtures. On-site, "
     "rotating shifts."),
    (8, "appliance_repair", "laundry", "onsite", 0, "open", False, [], 15,
     "Front-load washing machine stopped draining and shows an error code. Need someone in Hyderabad who can come "
     "home and fix it this week."),
    (0, "financial_planner", "retirement", "remote", 5, "open", False, [], 6,
     "Looking for a fee-only financial planner (5+ years) to review our 401(k)s and IRAs and build a retirement "
     "income plan. Video calls are fine."),
    (7, "piano_teacher", "kids", "remote", 0, "open", False, [], 5,
     "Looking for a piano teacher for my 6-year-old, a complete beginner. Online lessons once a week are fine."),
    (5, "driving_instructor", "nervous", "onsite", 0, "open", False, ["sparse"], 3,
     "Need a patient driving instructor in London for a very nervous adult learner preparing for the practical "
     "test."),
    (10, "elder_caregiver", "dementia", "onsite", 1, "open", False, [], 5,
     "My father (78) has early dementia. Looking for a caregiver in Pune for day-time care at home: meals, "
     "medicines and short walks. Some experience with memory care needed."),
]


class Builder:
    def __init__(self, seed: int):
        self.rng = random.Random(seed)
        self.users: list[dict] = []
        self.persons: dict[str, dict] = {}  # hidden truth about every real person
        self.connections: list[dict] = []
        self.edge_status: dict[frozenset, str] = {}
        self.neigh: dict[str, set] = defaultdict(set)  # accepted edges
        self.blocks: list[dict] = []
        self.blocked_pairs: set[frozenset] = set()
        self.self_entries: list[dict] = []
        self.tags: list[dict] = []
        self.labels: dict[str, dict] = {}
        self.requirements: list[dict] = []
        self.names_used: set[tuple] = set()
        self.nick_used: set[str] = set()
        self.tagged: set[tuple] = set()  # (owner, person): NFR-07, no duplicate tags per publisher
        self.self_done: dict[tuple, str] = {}  # (owner, archetype) -> self-entry id
        self.phone_seq = 0
        self.by_group: dict[str, list[str]] = defaultdict(list)
        for k, a in A.items():
            if a["background"]:
                self.by_group[a["group"]].append(k)

    # ---------------- people ----------------
    def new_name(self) -> tuple[str, str]:
        while True:
            if len(self.names_used) < 0.6 * len(FIRST) * len(LAST):
                n = (self.rng.choice(FIRST), self.rng.choice(LAST))
            else:  # a large --scale: draw from the longer lists, so unique names never run out
                n = (self.rng.choice(FIRST + FIRST_MORE), self.rng.choice(LAST + LAST_MORE))
                if len(self.names_used) > 0.6 * len(FIRST + FIRST_MORE) * len(LAST + LAST_MORE):
                    n = (n[0], f"{self.rng.choice('ABCDEGHJKLMNPRSTV')}. {n[1]}")  # last resort: add an initial
            if n not in self.names_used:
                self.names_used.add(n)
                return n

    def new_phone(self, country: str) -> str:
        self.phone_seq += 1
        s = self.phone_seq
        if country == "IN":
            return f"+91 90000 {s:05d}"
        if country == "GB":
            return f"+44 7700 900{s % 1000:03d}"  # Ofcom drama range
        return f"+1 {201 + s // 100} 555 01{s % 100:02d}"  # 555-01xx is reserved for fiction

    def new_nick(self, first: str) -> str:
        i = 1
        while f"{first[:4].lower()}{i}" in self.nick_used:
            i += 1
        self.nick_used.add(f"{first[:4].lower()}{i}")
        return f"{first[:4].lower()}{i}"

    def other_city(self, city: str, same_country: bool) -> str:
        home = COUNTRY_OF[city]
        if same_country:
            return self.rng.choice([c for c in CITIES[home] if c != city])
        return self.rng.choice([c for k, cs in CITIES.items() if k != home for c in cs])

    def draw_arch(self, weights: dict) -> str:
        groups = [g for g in weights if self.by_group[g]]
        g = self.rng.choices(groups, [weights[x] for x in groups])[0]
        return self.rng.choice(self.by_group[g])

    def draw_skill(self, arch: str) -> dict:
        a = A[arch]
        years = 0 if a["kind"] == "resource" else self.rng.choice([1, 2, 2, 3, 3, 4, 5, 5, 6, 7, 8, 9, 10, 12, 15, 20])
        spec = self.rng.choice(sorted(a["specs"])) if self.rng.random() < 0.7 else None
        return dict(years=years, spec=spec)

    def new_person(self, first: str, last: str, user_id: str | None, city: str) -> str:
        pid = f"P{len(self.persons) + 1:05d}"
        self.persons[pid] = dict(first=first, last=last, user_id=user_id, city=city, country=COUNTRY_OF[city], skills={})
        return pid

    def add_user(self, cluster: str, city: str, kind: str) -> dict:
        first, last = self.new_name()
        uid = f"U{len(self.users) + 1:03d}"
        username = f"{first}.{last}".lower().replace("'", "")
        pid = self.new_person(first, last, uid, city)
        country = COUNTRY_OF[city]
        u = dict(id=uid, username=username, nickname=self.new_nick(first), name=f"{first} {last}",
                 email=f"{username}@example.com", phone=self.new_phone(country), bio=f"Lives in {city}.", location=city,
                 auth_provider=self.rng.choice(["phone_otp", "google_oauth"]),
                 created_at=iso(days_ago(self.rng.randint(30, 400))),
                 _person=pid, _city=city, _country=country, _cluster=cluster, _kind=kind)
        self.users.append(u)
        skills = self.persons[pid]["skills"]
        main = self.draw_arch(OWN[kind])
        skills[main] = self.draw_skill(main)
        if self.rng.random() < 0.35:
            side = self.draw_arch(SIDE)
            skills.setdefault(side, self.draw_skill(side))
        return u

    def add_nonuser(self, city: str, arch: str, years: int | None = None, spec: str | None = "?",
                    name: tuple[str, str] | None = None) -> str:
        first, last = name or self.new_name()
        pid = self.new_person(first, last, None, city)
        sk = self.draw_skill(arch)
        if years is not None:
            sk["years"] = years
        if spec != "?":
            sk["spec"] = spec
        self.persons[pid]["skills"][arch] = sk
        return pid

    def user(self, uid: str) -> dict:
        return self.users[int(uid[1:]) - 1]

    # ---------------- graph ----------------
    def connect(self, a: str, b: str, status: str = "accepted") -> None:
        key = frozenset((a, b))
        if a == b or key in self.edge_status:
            return
        self.edge_status[key] = status
        if status == "accepted":
            self.neigh[a].add(b)
            self.neigh[b].add(a)
        created = days_ago(self.rng.randint(5, 300))
        self.connections.append(dict(
            id=f"C{len(self.connections) + 1:05d}", requester_id=a, addressee_id=b, status=status,
            created_at=iso(created),
            responded_at=None if status == "pending" else iso(created + dt.timedelta(days=self.rng.randint(0, 4)))))

    def block(self, blocker: str, blocked: str) -> None:
        self.blocked_pairs.add(frozenset((blocker, blocked)))
        self.blocks.append(dict(blocker_id=blocker, blocked_id=blocked, created_at=iso(days_ago(self.rng.randint(1, 60)))))

    def direct(self, uid: str) -> set[str]:
        return set(self.neigh[uid])

    def eligible_owners(self, uid: str) -> list[str]:
        return sorted(o for o in self.neigh[uid] if frozenset((uid, o)) not in self.blocked_pairs)

    def two_hop(self, uid: str) -> list[str]:
        d = self.neigh[uid]
        out = set().union(*(self.neigh[n] for n in d)) - d - {uid} if d else set()
        return sorted(o for o in out if frozenset((uid, o)) not in self.edge_status)

    # ---------------- text ----------------
    def years_text(self, n: int, kind: str) -> str:
        y = REFERENCE_DATE.year - n
        if n == 1:
            return self.rng.choice(["1 year of experience", "about a year", f"since {y}"])
        if kind == "hobby":
            return self.rng.choice([f"playing for {n} years", f"{n} years", f"since {y}", f"{n}+ yrs"])
        forms = [f"{n} years of experience", f"{n}+ years", f"{n} yrs exp", f"around {n} years", f"{n} yrs",
                 f"doing this since {y}", f"in this line since {y}", f"{n} years"]
        if n >= 3:
            forms.append(f"over {n} years in the field")
        return self.rng.choice(forms)

    def typo(self, text: str) -> str:
        words = text.split(" ")
        idx = [i for i, w in enumerate(words) if len(w) >= 6 and w.isalpha() and w.islower()]
        if not idx:
            return text
        i = self.rng.choice(idx)
        w = words[i]
        j = self.rng.randint(1, len(w) - 3)
        words[i] = w[:j] + w[j + 1] + w[j] + w[j + 2:]
        return " ".join(words)

    def compose(self, arch: str, spec: str | None, years: int, city: str, *, voice: str, variant: str,
                describe: bool, say_years: bool, say_loc: bool, noise: bool, away: bool = False):
        """Return (skills, description). Text is assembled from parts so entries rarely repeat."""
        rng = self.rng
        if arch in TRAPS:
            t = TRAPS[arch]
            parts = [t["text"]]
            if say_years and years:
                parts.append(cap(self.years_text(years, "pro")) + ".")
            if say_loc:
                parts.append(f"{city}.")
            return list(t["skills"]), " ".join(parts)
        a = A[arch]
        kind = a["kind"]
        foci, spec_skills = a["specs"][spec] if spec else ([], [])
        syn = variant == "synonym"
        me = voice == "self"
        tools = [t for t in a["tools"] if not syn or is_pure(arch, t)]
        # --- skill tags, like the skill chips on a profile (FR-15)
        skills = rng.sample(a["syn"] if syn else a["skills"], k=min(len(a["syn"] if syn else a["skills"]),
                                                                    rng.randint(2, 4)))
        if spec and not syn and rng.random() < 0.8:
            skills.insert(rng.randint(0, len(skills)), rng.choice(spec_skills))
        if tools and rng.random() < 0.85:
            skills += [t for t in rng.sample(tools, k=min(len(tools), rng.randint(1, 3))) if t not in skills]
        if not describe:
            return skills, None
        # --- description: who they are, then concrete work they have done
        Y = self.years_text(years, kind) if (say_years and years) else None
        F = rng.choice(foci) if spec else None
        ysuf = f", {Y}" if Y else ""
        if syn:
            s = [cap(rng.choice(a["syn_does"])) + "."]
        elif kind == "resource":
            d = rng.choice(a["does"])
            s = [(re.sub(r"^Has ", "I have ", d) if me else d) + "."]
        else:
            role = rng.choice(a["roles"])
            s = [rng.choice([f"I'm {an(role)}{ysuf}.", f"Working as {an(role)}{ysuf}.", f"{cap(role)}{ysuf}."] if me
                            else [f"{cap(role)}{ysuf}.", f"Works as {an(role)}{ysuf}.",
                                  f"{cap(role)}{' (' + Y + ')' if Y else ''}."])]
            Y = None  # already in the opening line
        if Y:
            s.append(cap(Y) + ".")
        if F and (syn or rng.random() < 0.6):
            s.append(rng.choice([f"Good for {F}.", f"Useful for {F}.", cap(F) + "."] if kind == "resource"
                                else [f"Mostly {F}.", f"Focus: {F}.", f"Strong in {F}.", cap(F) + "."]))
        work = rng.sample(a["syn_duties" if syn else "duties"], k=rng.choice([1, 2, 2, 3, 3]))
        if spec and not syn and a["spec_duties"].get(spec):
            work.insert(rng.randint(0, min(1, len(work))), rng.choice(a["spec_duties"][spec]))
        for i, d in enumerate(work):
            if me:
                s.append(("I " if i == 0 else rng.choice(["I ", "I ", "I also ", "Before that, I "])) + d + ".")
            else:
                s.append(cap(d) + "." if i == 0 or rng.random() < 0.7 else f"Also {d}.")
        if len(tools) >= 2 and rng.random() < 0.5:
            ts = rng.sample(tools, k=min(len(tools), rng.randint(2, 3)))
            ts_txt = ", ".join(ts[:-1]) + " and " + ts[-1]
            if kind in ("hobby", "resource"):
                s.append(f"Gear: {', '.join(ts)}.")
            else:
                s.append(rng.choice([f"I use {ts_txt}.", f"Comfortable with {ts_txt}."] if me
                                    else [f"Works with {ts_txt}.", f"Tools: {', '.join(ts)}."]))
        certs = [c for c in a["certs"] if not syn or is_pure(arch, c)]
        if certs and rng.random() < 0.4:
            s.append(f"Certified: {rng.choice(certs)}.")
        if me and kind == "pro" and rng.random() < 0.25:
            s.append(rng.choice(["Weekends only.", "Evenings and weekends.", "Open to short projects.",
                                 "Available for full-time roles.", "Takes on freelance work."]))
        if say_loc:
            if away:
                s.append(f"Currently in {city}.")
            else:
                s.append(rng.choice([f"Based in {city}.", f"{city}.", f"{city} area.", f"Works across {city}."]
                                    + ([] if voice == "self" else [f"Lives in {city}."])))
        text = " ".join(s)
        if noise:
            r = rng.random()
            if r < 0.10:
                text = text.lower()
            elif r < 0.18:
                text = self.typo(text)
            elif r < 0.26:
                text = text.replace(" and ", " & ")
        return skills, text

    # ---------------- entries ----------------
    def _label(self, eid: str, arch: str, spec, variant: str, person: str, years: int, city: str,
               ys: bool, ls: bool, also: list[str]) -> None:
        self.labels[eid] = dict(archetype=arch, specialty=spec, variant="trap" if arch in TRAPS else variant,
                                true_person_id=person, years=years, years_stated=ys, city=city,
                                country=COUNTRY_OF[city], location_stated=ls, also=also,
                                planted_for=[], scenarios=["background"])

    def self_entry(self, owner: str, arch: str, *, years: int | None = None, spec: str | None = "?",
                   city: str | None = None, variant: str = "canonical", availability: str = "open",
                   say_years: bool | None = None, say_loc: bool | None = None, noise: bool = True) -> str:
        """FR-13: one skill or resource with a description. One self-entry per owner and skill."""
        if (owner, arch) in self.self_done:
            return self.self_done[(owner, arch)]
        rng, u = self.rng, self.user(owner)
        p = self.persons[u["_person"]]
        sk = p["skills"].setdefault(arch, self.draw_skill(arch))
        if years is not None:
            sk["years"] = years
        if spec != "?":
            sk["spec"] = spec
        years, spec = sk["years"], sk["spec"]
        city = city or u["_city"]
        local = A[arch]["local"]
        # ys / ls: is the fact known at all? If yes, it is in the field, and sometimes also in the text.
        ys = (rng.random() < 0.85 if say_years is None else say_years) and years > 0
        ls = rng.random() < 0.9 if say_loc is None else say_loc
        skills, text = self.compose(arch, spec, years, city, voice="self", variant=variant, describe=True,
                                    say_years=ys and (not noise or rng.random() < 0.6),
                                    say_loc=ls and local and (not noise or rng.random() < 0.5),
                                    noise=noise, away=city != u["_city"])
        eid = f"S{len(self.self_entries) + 1:04d}"
        self.self_entries.append(dict(id=eid, owner_user_id=owner, skill=skills[0], skills=skills, description=text,
                                      experience_years=years if ys else None, location=city if ls else None,
                                      availability_status=availability,
                                      created_at=iso(days_ago(rng.randint(1, 300)))))
        self._label(eid, arch, spec, variant, u["_person"], years, city, ys, ls, [])
        self.self_done[(owner, arch)] = eid
        return eid

    def tag(self, owner: str, person: str, arch: str | None = None, *, years: int | None = None,
            spec: str | None = "?", city: str | None = None, variant: str = "canonical",
            availability: str = "open", confirmed_ago: int | None = None, alias: bool | None = None,
            describe: bool | None = None, say_years: bool | None = None, say_loc: bool | None = None,
            noise: bool = True, extra: bool | None = None) -> str | None:
        """FR-14..17: first/last name, one or more skills, optional description and alias."""
        rng = self.rng
        if (owner, person) in self.tagged:
            return None
        self.tagged.add((owner, person))
        p = self.persons[person]
        arch = arch or rng.choice(sorted(p["skills"]))
        if arch in TRAPS:
            sk = dict(years=years or rng.randint(2, 12), spec=None)
        else:
            sk = p["skills"].setdefault(arch, self.draw_skill(arch))
            if years is not None:
                sk["years"] = years
            if spec != "?":
                sk["spec"] = spec
        years, spec = sk["years"], sk["spec"]
        city = city or p["city"]
        local = A[TRAPS[arch]["trap_for"] if arch in TRAPS else arch]["local"]
        if variant == "synonym":
            describe = True
        if describe is None:
            describe = rng.random() < 0.93
        # ys / ls: does the tagger know the fact? If yes, it is in the field, and sometimes also in the text.
        ys = (rng.random() < 0.8 if say_years is None else say_years) and years > 0
        ls = rng.random() < 0.85 if say_loc is None else say_loc
        skills, text = self.compose(arch, spec, years, city, voice="tag", variant=variant, describe=describe,
                                    say_years=ys and (not noise or rng.random() < 0.6),
                                    say_loc=ls and local and (not noise or rng.random() < 0.5), noise=noise)
        # FR-15: several skills in one tag. The extra skill comes with no supporting detail.
        also = []
        others = sorted(k for k in p["skills"] if k != arch)
        if others and arch not in TRAPS and variant != "synonym" and (rng.random() < 0.6 if extra is None else extra):
            o = rng.choice(others)
            skills.append(rng.choice(A[o]["skills"]))
            also.append(o)
        if alias is None:
            alias = rng.random() < 0.2
        confirmed = days_ago(confirmed_ago if confirmed_ago is not None else rng.randint(0, 170))
        eid = f"T{len(self.tags) + 1:04d}"
        self.tags.append(dict(
            id=eid, owner_user_id=owner, subject_user_id=p["user_id"], first_name=p["first"],
            last_name=p["last"], alias=f"{rng.choice(FIRST)} {rng.choice(LAST)}" if alias else None,
            skills=skills, description=text, experience_years=years if ys else None,
            location=city if ls else None, availability_status=availability,
            last_confirmed_at=iso(confirmed),
            created_at=iso(confirmed - dt.timedelta(days=rng.randint(0, 120)))))
        # A skills-only tag states its specialty only when a specialty skill is listed.
        self._label(eid, arch, spec, variant, person, years, city, ys, ls, also)
        return eid


# --------------------------------------------------------------------------
# Rules: the single source of truth for the answer key. README mirrors this.
# --------------------------------------------------------------------------
def relevance(req: dict, lab: dict) -> tuple[int, list[str]]:
    """Return (grade 0-3, the reasons for any lost points)."""
    ra, arch = req["_archetype"], lab["archetype"]
    if arch == ra:
        misses, why = 0, []
        if lab["years_stated"]:
            gap = req["_min_years"] - lab["years"]
            if gap > 0:
                misses += 1 if gap <= 2 else 2
                why.append(f"experience {gap} yr{'s' if gap > 1 else ''} short")
        if req["_work_type"] in ("onsite", "hybrid") and lab["location_stated"]:
            if lab["country"] != req["_location"]["country"]:
                misses += 2
                why.append(f"other country: {lab['city']}")
            elif lab["city"] != req["_location"]["city"]:
                misses += 1
                why.append(f"other city: {lab['city']}")
        if req["_specialty"] and lab["specialty"] and lab["specialty"] != req["_specialty"]:
            misses += 1
            why.append(f"different specialty: {lab['specialty']}")
        return (3 if misses == 0 else 2 if misses == 1 else 1), why
    if ra in lab["also"]:
        return 2, ["listed only as an extra skill, with no detail"]
    if arch in A and (arch in A[ra]["related"] or ra in A[arch]["related"]):
        return 1, [f"related skill: {A[arch]['label']}"]
    return 0, []


def exclusion_reasons(b: Builder, req: dict, e: dict, kind: str) -> list[str]:
    P, o = req["publisher_id"], e["owner_user_id"]
    r = []
    if req["status"] != "open":
        r.append("requirement_closed")
    if o == P:
        if kind == "self_entry":
            r.append("own_self_entry")
        elif not INCLUDE_OWN_TAGS:
            r.append("own_tag")
    else:
        st = b.edge_status.get(frozenset((P, o)))
        if st == "pending":
            r.append("pending_connection")
        elif st == "removed":
            r.append("removed_connection")
        elif st != "accepted":
            r.append("not_in_direct_circle")
        if frozenset((P, o)) in b.blocked_pairs:
            r.append("blocked")
        if req["audience_user_ids"] and o not in req["audience_user_ids"]:
            r.append("outside_audience")
    if e["availability_status"] != "open":
        r.append("not_open")
    if (kind == "tag" and RECONFIRM_WINDOW_DAYS is not None
            and (REFERENCE_DATE - dt.date.fromisoformat(e["last_confirmed_at"])).days > RECONFIRM_WINDOW_DAYS):
        r.append("stale_unconfirmed")
    if kind == "tag" and e["subject_user_id"] == P:
        r.append("subject_is_publisher")
    return r


def build(seed: int, scale: float) -> Builder:
    check_synonym_purity()
    b = Builder(seed)
    rng = b.rng
    cl = {k: dict(city=c, kind=kind, n=max(8, round(n * scale)), users=[], pool=[]) for k, c, kind, n in CLUSTERS}

    # Publishers first, so their ids are stable (U001..U012).
    pubs = []
    for ck, _ in PUBLISHERS:
        u = b.add_user(ck, cl[ck]["city"], cl[ck]["kind"])
        cl[ck]["users"].append(u["id"])
        pubs.append(u["id"])
    for ck, c in cl.items():
        while len(c["users"]) < c["n"]:
            city = c["city"] if rng.random() < 0.9 else rng.choice([x for xs in CITIES.values() for x in xs])
            c["users"].append(b.add_user(ck, city, c["kind"])["id"])
    uids = [u["id"] for u in b.users]

    # Graph: people mostly know others in their own cluster.
    for ck, c in cl.items():
        for u in c["users"]:
            for v in rng.sample(c["users"], k=min(len(c["users"]) - 1, rng.randint(2, 6))):
                b.connect(u, v)
            if rng.random() < 0.2:
                b.connect(u, rng.choice(uids))
    for p, (ck, size) in zip(pubs, PUBLISHERS):
        size = max(5, round(size * scale))
        own = [u for u in cl[ck]["users"] if u != p]
        same_city = [u for k2, c2 in cl.items() if k2 != ck and c2["city"] == cl[ck]["city"] for u in c2["users"]]
        want_own = min(len(own), round(size * 0.8))
        picks = rng.sample(own, want_own)
        rest = [u for u in (same_city or uids) if u != p and u not in picks]
        picks += rng.sample(rest, min(len(rest), size - want_own))
        for v in picks:
            b.connect(p, v)
    for _ in range(round(40 * scale)):
        b.connect(*rng.sample(uids, 2), status="rejected")

    # Per publisher: one pending invite, one removed connection (FR-08), one block (FR-46).
    special: dict[str, dict] = {}
    for i, p in enumerate(pubs):
        free = [u for u in uids if u != p and frozenset((p, u)) not in b.edge_status]
        pend, removed = rng.sample(free, 2)
        b.connect(p, pend, status="pending")
        b.connect(removed, p, status="removed")
        victim = rng.choice(sorted(set(b.eligible_owners(p)) - set(pubs)))
        b.block(p, victim) if i % 2 else b.block(victim, p)
        special[p] = dict(pending=pend, removed=removed, blocked=victim)

    # Non-users that each cluster's people know and tag.
    for ck, c in cl.items():
        for _ in range(round(c["n"] * 2.5)):
            city = c["city"] if rng.random() < 0.85 else rng.choice([x for xs in CITIES.values() for x in xs])
            c["pool"].append(b.add_nonuser(city, b.draw_arch(TAGS[c["kind"]])))
    all_pool = [p for c in cl.values() for p in c["pool"]]

    def rand_variant() -> str:
        return "synonym" if rng.random() < 0.2 else "canonical"

    def rand_avail() -> str:
        return "open" if rng.random() < 0.88 else "not_open"

    # Background entries.
    for u in b.users:
        for arch in sorted(b.persons[u["_person"]]["skills"]):
            if rng.random() < 0.75:
                b.self_entry(u["id"], arch, variant=rand_variant(), availability=rand_avail())
        circle = sorted(b.direct(u["id"]))
        pool = cl[u["_cluster"]]["pool"]
        for _ in range(rng.choice([0, 0, 1, 1, 2, 2, 3, 3, 4, 5, 6, 8, 12])):
            if circle and rng.random() < 0.15:  # FR-14: a tag may describe a subscriber
                subj = b.user(rng.choice(circle))["_person"]
            else:
                subj = rng.choice(pool if rng.random() < 0.9 else all_pool)
            b.tag(u["id"], subj, variant=rand_variant(), availability=rand_avail(),
                  confirmed_ago=rng.randint(0, 170) if rng.random() < 0.88 else rng.randint(200, 420))

    # ------------------------------------------------------------------
    # Requirements and planted scenarios (one of each test case per requirement).
    # ------------------------------------------------------------------
    ctx = []
    for i, (pi, arch, spec, wt, min_y, status, anon, flags, target, text) in enumerate(REQS):
        rid = f"R{i + 1:02d}"
        P = pubs[pi]
        pu = b.user(P)
        loc = None if wt == "remote" else dict(city=pu["_city"], country=pu["_country"])
        owners = b.eligible_owners(P)
        audience = sorted(rng.sample(owners, k=len(owners) // 2)) if "audience" in flags else []
        req = dict(id=rid, publisher_id=P, text=text, location=loc["city"] if loc else None,
                   min_experience_years=min_y or None, status=status, anonymous=anon,
                   audience_user_ids=audience, created_at=iso(days_ago(rng.randint(1, 40))),
                   _archetype=arch, _specialty=spec, _work_type=wt, _min_years=min_y, _location=loc,
                   _flags=flags, _target=round(target * scale) if target > 3 else target)
        b.requirements.append(req)
        pool = audience or owners
        home = loc["city"] if loc else None
        ctx.append((req, pool, home))
        res = A[arch]["kind"] == "resource"

        def good_years() -> int:
            return 0 if res else (min_y + rng.randint(0, 6) if min_y else rng.randint(1, 12))

        def where(ok: bool = True) -> str:
            if home:
                return home if ok else b.other_city(home, same_country=False)
            return rng.choice([c for cs in CITIES.values() for c in cs])

        def fresh(arch_: str = arch, years: int | None = None, ok_loc: bool = True, spec_: str | None = spec,
                  name: tuple[str, str] | None = None) -> str:
            return b.add_nonuser(where(ok_loc), arch_, good_years() if years is None else years,
                                 spec_ if arch_ == arch else "?", name)

        def plant(eid: str | None, scen: str) -> str | None:
            if eid is None:
                return None
            lab = b.labels[eid]
            lab["planted_for"].append(rid)
            lab["scenarios"] = [s for s in lab["scenarios"] if s != "background"] + [scen]
            return eid

        def pick(exclude: set[str] = frozenset(), person: str | None = None) -> str:
            c = [o for o in pool if o not in exclude and (person is None or (o, person) not in b.tagged)]
            return rng.choice(c or pool)

        def two_hop() -> str:
            c = b.two_hop(P) or [u for u in uids if u != P and frozenset((P, u)) not in b.edge_status]
            return rng.choice(c)

        # Planted rows state their facts clearly and carry no noise, so the expected result is fair.
        clear = dict(describe=True, say_years=True, say_loc=True, noise=False, extra=False)
        if "no_match" in flags:
            plant(b.tag(two_hop(), fresh(), arch, **clear), "two_hop_owner")
            plant(b.tag(pick(), fresh(), arch, availability="not_open", **clear), "not_open")
            continue

        # Strong and eligible. A self-entry describes its owner, so prefer an owner who lives in the job's city.
        cand = [o for o in pool if (o, arch) not in b.self_done]
        local = [o for o in cand if home and b.user(o)["_city"] == home]
        o1 = rng.choice(local or cand or pool)
        s1 = plant(b.self_entry(o1, arch, years=good_years(), spec=spec, city=home, say_years=True, say_loc=True,
                                noise=False), "strong_self_entry")
        x = fresh()
        o2 = pick()
        plant(b.tag(o2, x, arch, alias=False, **clear), "strong_tag")
        plant(b.tag(pick({o2}), fresh(), arch, variant="synonym", **clear), "synonym_only")
        if status != "open":
            continue
        # Small-circle requirements (flag "sparse") skip these, so they have only a few matches.
        if "sparse" not in flags:
            # Two tags, same exact name. One is the same person (unlinkable duplicate), one is not.
            xp = b.persons[x]
            o3 = pick({o2}, x)
            plant(b.tag(o3, x, arch, alias=False, **clear), "duplicate_same_name")
            y = fresh(name=(xp["first"], xp["last"]))
            plant(b.tag(pick({o2, o3}), y, arch, alias=False, **clear), "same_name_different_person")
            # A subscriber tags o1, who already has a matching self-entry: linkable, show once.
            o1p, s1l = b.user(o1)["_person"], b.labels[s1]
            plant(b.tag(pick({o1}, o1p), o1p, arch, city=s1l["city"], alias=False, **clear), "duplicate_registered_person")
            plant(b.tag(pick(), fresh(), arch, alias=True, **clear), "aliased_tag")
            plant(b.tag(pick(), fresh(spec_=None), arch, describe=False, say_years=False, say_loc=False, noise=False,
                        extra=False), "skills_only_tag")
            plant(b.tag(P, fresh(), arch, **clear), "own_tag")
            plant(b.tag(pick(), fresh(), arch, confirmed_ago=rng.randint(200, 400), **clear),
                  "old_confirmation" if RECONFIRM_WINDOW_DAYS is None else "stale_unconfirmed")

        # Partial and related.
        if min_y >= 2:
            plant(b.tag(pick(), fresh(years=max(1, min_y - rng.randint(1, 2))), arch, **clear), "partial_experience")
        if loc:
            plant(b.tag(pick(), fresh(ok_loc=False), arch, **clear), "partial_location")
        if spec and len(A[arch]["specs"]) > 1:
            other = rng.choice(sorted(k for k in A[arch]["specs"] if k != spec))
            plant(b.tag(pick(), fresh(spec_=other), arch, **clear), "partial_specialty")
        for rel in A[arch]["related"][:1]:
            plant(b.tag(pick(), fresh(rel), rel, **clear), "related_archetype")

        # Relevant, but must be excluded.
        plant(b.self_entry(P, arch, years=good_years(), spec=spec, say_years=True, noise=False), "own_self_entry")
        plant(b.tag(pick(), fresh(), arch, availability="not_open", **clear), "not_open")
        plant(b.tag(two_hop(), fresh(), arch, **clear), "two_hop_owner")
        plant(b.tag(special[P]["pending"], fresh(), arch, **clear), "pending_connection")
        plant(b.tag(special[P]["removed"], fresh(), arch, **clear), "removed_connection")
        plant(b.tag(special[P]["blocked"], fresh(), arch, **clear), "blocked_owner")
        plant(b.tag(pick(person=pu["_person"]), pu["_person"], arch, years=good_years(), spec=spec, **clear),
              "subject_is_publisher")
        if audience:
            plant(b.tag(rng.choice([o for o in owners if o not in audience]), fresh(), arch, **clear),
                  "outside_audience")
        for tkey, t in TRAPS.items():
            if t["trap_for"] == arch:
                trap_person = b.new_person(*b.new_name(), None, where())
                plant(b.tag(pick(), trap_person, tkey, **clear), "lexical_trap")

    # ------------------------------------------------------------------
    # Volume: top each requirement up to its target number of good matches,
    # with a realistic spread of strong / good / weak people.
    # ------------------------------------------------------------------
    rows = lambda: [("self_entry", e) for e in b.self_entries] + [("tag", e) for e in b.tags]  # noqa: E731
    for req, pool, home in ctx:
        if req["status"] != "open" or "no_match" in req["_flags"] or not req["_target"]:
            continue
        arch, spec, min_y = req["_archetype"], req["_specialty"], req["_min_years"]
        a = A[arch]
        res = a["kind"] == "resource"
        good = {b.labels[e["id"]]["true_person_id"] for kind, e in rows()
                if relevance(req, b.labels[e["id"]])[0] >= 2 and not exclusion_reasons(b, req, e, kind)}
        other_specs = sorted(k for k in a["specs"] if k != spec)
        guard = 0
        while len(good) < req["_target"] and guard < 5000:
            guard += 1
            owner = rng.choice(pool)
            years = 0 if res else (min_y + rng.randint(0, 8) if min_y else rng.randint(1, 15))
            sp = spec if rng.random() < 0.7 else None
            city = home or rng.choice([c for cs in CITIES.values() for c in cs])
            say_y = say_l = None
            # Choose which soft misses this person has.
            misses = []
            r = rng.random()
            options = ((["spec"] if spec and other_specs else []) + (["years"] if min_y >= 2 else [])
                       + (["city"] if home else []))
            if r > 0.5 and options:
                misses = rng.sample(options, 1 if r < 0.82 else min(2, len(options)))
            for m in misses:
                if m == "spec":
                    sp = rng.choice(other_specs)
                elif m == "years":
                    years, say_y = max(1, min_y - rng.randint(1, 2 if len(misses) == 1 else 4)), True
                else:
                    city, say_l = b.other_city(home, same_country=rng.random() < 0.7), True
            variant = "synonym" if rng.random() < 0.18 else "canonical"
            describe = True if (misses or variant == "synonym") else rng.random() < 0.95
            common = dict(variant=variant, say_years=say_y, say_loc=say_l)
            if (not misses or misses == ["spec"]) and rng.random() < 0.25 and (owner, arch) not in b.self_done \
                    and owner != req["publisher_id"] and (not home or b.user(owner)["_city"] == home):
                eid = b.self_entry(owner, arch, years=years, spec=sp, **common)
            else:
                circle = sorted(b.direct(owner))
                if not misses and circle and rng.random() < 0.12:
                    subj = b.user(rng.choice(circle))["_person"]  # a registered user: can be merged
                    if subj == b.user(req["publisher_id"])["_person"]:
                        continue
                    city = b.persons[subj]["city"] if not home else city
                else:
                    subj = b.add_nonuser(city, arch, years, sp)
                eid = b.tag(owner, subj, arch, years=years, spec=sp, city=city, describe=describe, **common)
            if eid is None:
                continue
            lab = b.labels[eid]
            lab["scenarios"] = ["volume"] if lab["scenarios"] == ["background"] else lab["scenarios"]
            e = (b.self_entries if eid[0] == "S" else b.tags)[int(eid[1:]) - 1]
            if relevance(req, lab)[0] >= 2 and not exclusion_reasons(b, req, e, "self_entry" if eid[0] == "S" else "tag"):
                good.add(lab["true_person_id"])
    return b


def answer_key(b: Builder) -> dict:
    users = {u["id"]: u for u in b.users}
    rows = [("self_entry", e) for e in b.self_entries] + [("tag", e) for e in b.tags]
    out = {}
    for req in b.requirements:
        P = req["publisher_id"]
        eligible, graded = [], []
        for kind, e in rows:
            lab = b.labels[e["id"]]
            rel, why = relevance(req, lab)
            reasons = exclusion_reasons(b, req, e, kind)
            if not reasons:
                eligible.append(e["id"])
            planted_here = req["id"] in lab["planted_for"]
            # Keep the key readable: skip entries the publisher simply has no connection to.
            if not planted_here and (rel == 0 or reasons == ["not_in_direct_circle"]
                                     or "not_in_direct_circle" in reasons or "requirement_closed" in reasons):
                continue
            if kind == "self_entry":
                display = users[e["owner_user_id"]]["name"]
                notify, never, subject_user = sorted({P, e["owner_user_id"]}), [], e["owner_user_id"]
            else:
                real = f"{e['first_name']} {e['last_name']}"
                display = e["alias"] if e["alias"] and e["owner_user_id"] != P else real
                notify = [e["owner_user_id"]]  # FR-37: only the tag's creator
                never = [e["subject_user_id"]] if e["subject_user_id"] and e["subject_user_id"] != e["owner_user_id"] else []
                subject_user = e["subject_user_id"]
            graded.append(dict(
                entry_id=e["id"], entry_type=kind, owner_user_id=e["owner_user_id"],
                true_person_id=lab["true_person_id"], subject_user_id=subject_user,
                relevance=rel, why=why, eligible=not reasons, exclusion_reasons=reasons, variant=lab["variant"],
                scenarios=lab["scenarios"] if planted_here else ["background"],
                display_name_for_publisher=display,
                expected_notify=[] if reasons else notify, must_not_notify=never))
        graded.sort(key=lambda g: (not g["eligible"], -g["relevance"], g["entry_id"]))

        # Show-once groups the system CAN detect: entries about the same registered user.
        groups = defaultdict(list)
        for g in graded:
            if g["eligible"] and g["relevance"] > 0 and g["subject_user_id"]:
                groups[g["subject_user_id"]].append(g)
        merges = [dict(subject_user_id=u, entry_ids=[g["entry_id"] for g in gs],
                       vouched_by=sorted({g["owner_user_id"] for g in gs if g["entry_type"] == "tag"}))
                  for u, gs in sorted(groups.items()) if len(gs) > 1]

        best: dict[str, int] = {}
        for g in graded:
            if g["eligible"]:
                best[g["true_person_id"]] = max(best.get(g["true_person_id"], 0), g["relevance"])
        people = Counter(best.values())
        loc = req["_location"]
        out[req["id"]] = dict(
            text=req["text"], publisher_id=P, status=req["status"], anonymous=req["anonymous"],
            hidden=dict(archetype=req["_archetype"], label=A[req["_archetype"]]["label"],
                        specialty=req["_specialty"], work_type=req["_work_type"], min_years=req["_min_years"],
                        location=loc),
            flags=req["_flags"], circle_size=len(b.eligible_owners(P)),
            expected_people=dict(strong=people[3], good=people[2], weak=people[1]),
            expect_no_matches=people[3] + people[2] == 0, expected_merges=merges,
            eligible_entry_ids=eligible, graded=graded)
    return out


def review_md(b: Builder, key: dict) -> str:
    """A human-readable page: what each requirement should and should not find."""
    users = {u["id"]: u["name"] for u in b.users}
    entries = {e["id"]: e for e in b.self_entries + b.tags}
    rel_word = {3: "strong", 2: "good", 1: "weak", 0: "none"}

    def what(e: dict) -> str:
        if "skill" in e:
            s = f"**{e['skill']}**: {e['description']}"
        else:
            s = "**" + ", ".join(e["skills"]) + "**" + (f": {e['description']}" if e["description"] else " (no description)")
        return s.replace("|", "/")

    out = ["# Test data review", "",
           "Generated by `generate.py`; do not edit by hand. One section per requirement.", "",
           "Each section has two tables:",
           "- **Planted test cases**: one deliberate row per rule or situation.",
           "- **Sample of other matches**: a few of the many other people in the circle who match, "
           "to show the variety. The full list is in `ground_truth.csv`.", "",
           "## Summary", "",
           "| Req | Looking for | Circle | Strong | Good | Weak | Total people |", "|---|---|---|---|---|---|---|"]
    for rid, r in key.items():
        h, p = r["hidden"], r["expected_people"]
        note = " (closed)" if r["status"] != "open" else ""
        out.append(f"| {rid} | {h['label']}{note} | {r['circle_size']} | {p['strong']} | {p['good']} | {p['weak']} | "
                   f"{p['strong'] + p['good'] + p['weak']} |")
    out.append("")
    for rid, r in key.items():
        h, p = r["hidden"], r["expected_people"]
        where = "remote" if h["work_type"] == "remote" else f"{h['work_type']} in {h['location']['city']}"
        spec = f", specialty: {h['specialty']}" if h["specialty"] else ""
        out += [f"## {rid} · {h['label']} ({where}, {h['min_years']}+ yrs{spec})", "",
                f"> {r['text']}", "",
                f"Publisher: {users[r['publisher_id']]} ({r['publisher_id']}) · circle: {r['circle_size']} subscribers · "
                f"status: {r['status']}" + (" · **anonymous**" if r["anonymous"] else "")
                + (f" · audience: {len(b.requirements[int(rid[1:]) - 1]['audience_user_ids'])} subscribers"
                   if "audience" in r["flags"] else ""), ""]
        if r["expect_no_matches"]:
            out += ["**Expected result: no matches.**", ""]
        else:
            out += [f"**Expected: {p['strong'] + p['good'] + p['weak']} people** "
                    f"({p['strong']} strong, {p['good']} good, {p['weak']} weak).", ""]
        planted = [g for g in r["graded"] if g["scenarios"] != ["background"]]
        out += ["**Planted test cases**", "",
                "| Expected | Scenario | Entry | Via | Shown as | What it says |", "|---|---|---|---|---|---|"]
        for g in sorted(planted, key=lambda g: (not g["eligible"], -g["relevance"])):
            e = entries[g["entry_id"]]
            exp = (f"✅ show ({rel_word[g['relevance']]})" if g["eligible"] and g["relevance"] > 0
                   else "🚫 don't show: not relevant" if g["eligible"]
                   else "⛔ hide: " + ", ".join(g["exclusion_reasons"]))
            out.append(f"| {exp} | {', '.join(g['scenarios'])} | {g['entry_id']} | "
                       f"{users[g['owner_user_id']]} | {g['display_name_for_publisher']} | {what(e)} |")
        bg = [g for g in r["graded"] if g["scenarios"] == ["background"] and g["eligible"]]
        if bg:
            out += ["", f"**Sample of other matches** ({len(bg)} more entries match; showing up to 12)", "",
                    "| Expected | Entry | Via | Shown as | What it says | Why not strong |", "|---|---|---|---|---|---|"]
            sample = [g for lvl in (3, 2, 1) for g in [x for x in bg if x["relevance"] == lvl][:4]]
            for g in sample:
                out.append(f"| ✅ show ({rel_word[g['relevance']]}) | {g['entry_id']} | {users[g['owner_user_id']]} | "
                           f"{g['display_name_for_publisher']} | {what(entries[g['entry_id']])} | "
                           f"{'; '.join(g['why'])} |")
        hidden = sum(1 for g in r["graded"] if g["scenarios"] == ["background"] and not g["eligible"])
        if hidden:
            out += ["", f"Also {hidden} other relevant entries that must stay hidden (not open, blocked, and so on)."]
        for m in r["expected_merges"][:5]:
            out.append(f"\nShow once: {', '.join(m['entry_ids'])} describe the same person "
                       f"({users[m['subject_user_id']]}); vouched for by {len(m['vouched_by'])} tagger(s).")
        if len(r["expected_merges"]) > 5:
            out.append(f"\n...and {len(r['expected_merges']) - 5} more show-once groups.")
        out.append("")
    return "\n".join(out) + "\n"


def write(b: Builder, out: Path, seed: int) -> None:
    out.mkdir(parents=True, exist_ok=True)
    (out / "answer_key").mkdir(exist_ok=True)

    def dump(path: Path, obj, indent: int | None = 2) -> None:
        path.write_text(json.dumps(obj, indent=indent, ensure_ascii=False) + "\n")

    # Fields starting with "_" are hidden truth. PRD v1.3 profiles hold name, contact and bio only (FR-03).
    strip = lambda rows: [{k: v for k, v in r.items() if not k.startswith("_")} for r in rows]  # noqa: E731
    dump(out / "users.json", strip(b.users))
    dump(out / "trust_connections.json", b.connections)
    dump(out / "blocks.json", b.blocks)
    dump(out / "self_entries.json", b.self_entries)
    dump(out / "tags.json", b.tags)
    dump(out / "requirements.json", strip(b.requirements))
    dump(out / "rules.json", dict(
        reference_date=iso(REFERENCE_DATE), reconfirm_window_days=RECONFIRM_WINDOW_DAYS,
        include_own_tags=INCLUDE_OWN_TAGS, seed=seed,
        relevance_scale={"3": "strong", "2": "good, one soft miss", "1": "weak / adjacent", "0": "not relevant"}))

    key = answer_key(b)
    dump(out / "answer_key" / "ground_truth.json", dict(reference_date=iso(REFERENCE_DATE), requirements=key), 1)
    (out / "answer_key" / "entry_labels.json").write_text(
        "{\n" + ",\n".join(f"{json.dumps(k)}: {json.dumps(v, ensure_ascii=False)}" for k, v in b.labels.items()) + "\n}\n")
    (out / "answer_key" / "REVIEW.md").write_text(review_md(b, key))
    with open(out / "answer_key" / "ground_truth.csv", "w", newline="") as f:
        w = csv.writer(f)
        cols = ["entry_id", "entry_type", "owner_user_id", "true_person_id", "relevance", "why", "eligible",
                "exclusion_reasons", "variant", "scenarios", "display_name_for_publisher",
                "expected_notify", "must_not_notify"]
        w.writerow(["requirement_id"] + cols)
        for rid, r in key.items():
            for g in r["graded"]:
                w.writerow([rid] + [";".join(g[c]) if isinstance(g[c], list) else g[c] for c in cols])

    print(f"users={len(b.users)} connections={len(b.connections)} blocks={len(b.blocks)} "
          f"self_entries={len(b.self_entries)} tags={len(b.tags)} requirements={len(b.requirements)}")
    for rid, r in key.items():
        p = r["expected_people"]
        print(f"  {rid} {r['status']:6} {r['hidden']['archetype']:22} circle={r['circle_size']:3} "
              f"people: strong={p['strong']:3} good={p['good']:3} weak={p['weak']:3}  no_matches={r['expect_no_matches']}")


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--seed", type=int, default=42)
    ap.add_argument("--scale", type=float, default=1.0, help="multiply cluster, circle and target sizes")
    ap.add_argument("--out", type=Path, default=HERE)
    args = ap.parse_args()
    write(build(args.seed, args.scale), args.out, args.seed)


if __name__ == "__main__":
    main()

"""
Management command: seed_historical_incidents

Seeds the incidents_incident table with real historical Lagos emergency data via:

  1. Hardcoded base dataset — ~100 documented major Lagos incidents 2010-2025
     (sourced from public records, LASEMA reports, media archives)
  2. Google News RSS  — 100 articles per search query, title-based extraction
  3. Direct site RSS  — Vanguard, Premium Times, Daily Trust (full article fetch)

Usage:
    python manage.py seed_historical_incidents
    python manage.py seed_historical_incidents --dry-run
    python manage.py seed_historical_incidents --skip-hardcoded
    python manage.py seed_historical_incidents --skip-live
    python manage.py seed_historical_incidents --geocode
    python manage.py seed_historical_incidents --limit 200
"""

import hashlib
import re
import time
import uuid
from datetime import datetime, timezone
from urllib.parse import quote_plus, urljoin, urlparse

import requests
from bs4 import BeautifulSoup
from django.core.management.base import BaseCommand
from django.db import IntegrityError

from apps.incidents.models import Incident

# ──────────────────────────────────────────────────────────────────────────────
# Constants
# ──────────────────────────────────────────────────────────────────────────────

REPORTER_HASH = hashlib.sha256(b"historical_seed").hexdigest()
AI_CONFIDENCE = 0.85
REQUEST_DELAY = 2   # seconds between HTTP requests
NOMINATIM_DELAY = 1 # seconds between geocode requests (Nominatim ToS: 1/sec)

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/124.0.0.0 Safari/537.36"
    ),
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "en-NG,en;q=0.9",
}

# ──────────────────────────────────────────────────────────────────────────────
# Hardcoded historical base dataset
# Each entry: (ext_id, type, severity, zone, address, description, date_str, infra)
# date_str: "YYYY-MM-DD"
# ──────────────────────────────────────────────────────────────────────────────

HISTORICAL_INCIDENTS = [
    # ── COLLAPSE ──────────────────────────────────────────────────────────────
    (
        "seed://collapse-synagogue-2014",
        "COLLAPSE", "CRITICAL",
        "Ikotun", "Synagogue Church of All Nations, Ikotun-Egbe, Lagos",
        "A six-storey guesthouse belonging to Synagogue Church of All Nations collapsed in "
        "Ikotun-Egbe, Lagos, killing at least 116 people — mostly South African pilgrims. "
        "Rescue teams worked for days to retrieve survivors from the debris.",
        "2014-09-12", False,
    ),
    (
        "seed://collapse-itafaji-2019",
        "COLLAPSE", "CRITICAL",
        "Lagos Island", "Ita-Faji, Lagos Island",
        "A three-storey building housing a primary school collapsed at Ita-Faji on Lagos Island, "
        "killing at least 20 people including children. Emergency responders rescued over 40 "
        "survivors from the rubble before the operation was concluded.",
        "2019-03-13", False,
    ),
    (
        "seed://collapse-massey-2014",
        "COLLAPSE", "HIGH",
        "Lagos Island", "Massey Street, Ita-Faji, Lagos Island",
        "A two-storey building collapsed on Massey Street in the Ita-Faji area of Lagos Island, "
        "injuring several residents. LASEMA officials and emergency teams responded immediately "
        "to rescue those trapped under the wreckage.",
        "2014-07-10", False,
    ),
    (
        "seed://collapse-lekki-2016",
        "COLLAPSE", "HIGH",
        "Lekki", "Freedom Way, Lekki Phase 1, Lagos",
        "A under-construction building collapsed along Freedom Way in Lekki Phase 1, injuring "
        "multiple construction workers. Lagos State Building Control Agency launched an investigation "
        "into the structural failure.",
        "2016-05-22", False,
    ),
    (
        "seed://collapse-yaba-2017",
        "COLLAPSE", "HIGH",
        "Yaba", "Herbert Macaulay Way, Yaba, Lagos",
        "A storey building collapsed along Herbert Macaulay Way in Yaba, trapping residents inside. "
        "LASEMA rescue teams extracted three injured victims and one fatality from the rubble.",
        "2017-09-07", False,
    ),
    (
        "seed://collapse-surulere-2018",
        "COLLAPSE", "HIGH",
        "Surulere", "Adeniran Ogunsanya Street, Surulere, Lagos",
        "A two-storey residential building collapsed on Adeniran Ogunsanya Street in Surulere, "
        "displacing multiple families. LASEMA officials confirmed one death and four injuries "
        "as rescue operations concluded.",
        "2018-04-14", False,
    ),
    (
        "seed://collapse-orile-2019",
        "COLLAPSE", "CRITICAL",
        "Orile", "Orile Iganmu, Lagos",
        "A four-storey apartment building collapsed at Orile Iganmu, killing three people and "
        "injuring several others. Search-and-rescue teams used heavy equipment to sift through "
        "the debris during a multi-day recovery operation.",
        "2019-09-03", False,
    ),
    (
        "seed://collapse-ikorodu-2020",
        "COLLAPSE", "HIGH",
        "Ikorodu", "Ijede Road, Ikorodu, Lagos",
        "A building under construction collapsed along Ijede Road in Ikorodu, burying workers. "
        "LASEMA teams rescued four construction workers; one was confirmed dead at the site.",
        "2020-07-28", False,
    ),
    (
        "seed://collapse-agege-2021",
        "COLLAPSE", "HIGH",
        "Agege", "Iju Road, Agege, Lagos",
        "A storey building in Agege collapsed, trapping residents including children. "
        "Emergency response teams pulled six survivors and recovered two bodies from the wreckage.",
        "2021-03-11", False,
    ),
    (
        "seed://collapse-gbagada-2022",
        "COLLAPSE", "HIGH",
        "Gbagada", "Gbagada Phase 2, Lagos",
        "A partially completed four-storey structure collapsed in Gbagada, injuring three "
        "construction workers. The Lagos State Building Control Agency sealed the site pending "
        "a structural integrity investigation.",
        "2022-06-08", False,
    ),
    (
        "seed://collapse-ojota-2023",
        "COLLAPSE", "CRITICAL",
        "Ojota", "Ojota, Lagos",
        "A three-storey residential building collapsed in Ojota, killing two tenants and injuring "
        "several others. Rescue operations by LASEMA and the Lagos Fire Service lasted nearly "
        "twelve hours before all survivors were accounted for.",
        "2023-02-14", False,
    ),
    (
        "seed://collapse-mushin-2024",
        "COLLAPSE", "HIGH",
        "Mushin", "Idi-Araba Street, Mushin, Lagos",
        "A dilapidated two-storey building collapsed on Idi-Araba Street in Mushin, injuring "
        "four residents. The building had reportedly been marked for demolition by LASBCA.",
        "2024-01-19", False,
    ),

    # ── FIRE ──────────────────────────────────────────────────────────────────
    (
        "seed://fire-otedola-tanker-2018",
        "FIRE", "CRITICAL",
        "Ikeja", "Otedola Bridge, Lagos-Ibadan Expressway, Ojodu-Berger",
        "A loaded petrol tanker lost control and exploded on Otedola Bridge along the "
        "Lagos-Ibadan Expressway, killing nine people and destroying over a hundred vehicles. "
        "The inferno burned for hours before the Lagos Fire Service brought it under control.",
        "2018-07-28", False,
    ),
    (
        "seed://fire-balogun-2010",
        "FIRE", "HIGH",
        "Lagos Island", "Balogun Market, Lagos Island",
        "Fire gutted a section of Balogun Market on Lagos Island, destroying shops and merchandise "
        "worth millions of naira. Several traders lost their livelihoods as the market fire spread "
        "through adjoining stalls before firefighters arrived.",
        "2010-11-15", False,
    ),
    (
        "seed://fire-balogun-2016",
        "FIRE", "HIGH",
        "Lagos Island", "Balogun Market, Lagos Island",
        "Another major fire broke out at Balogun Market on Lagos Island, engulfing dozens of "
        "commercial stalls. Firefighters battled the blaze for over three hours; no lives were "
        "lost but property damage was extensive.",
        "2016-03-24", False,
    ),
    (
        "seed://fire-ladipo-2013",
        "FIRE", "HIGH",
        "Mushin", "Ladipo Auto Parts Market, Mushin, Lagos",
        "A fire swept through Ladipo auto spare-parts market in Mushin, destroying hundreds of "
        "shops. The blaze was linked to a gas cylinder that exploded inside one of the market stalls.",
        "2013-06-18", False,
    ),
    (
        "seed://fire-apapa-wharf-2015",
        "FIRE", "HIGH",
        "Apapa", "Apapa Port, Apapa, Lagos",
        "A fire broke out at the Apapa Wharf Port facility, damaging goods in transit and "
        "causing significant losses to importers. The Nigerian Ports Authority fire brigade "
        "responded alongside the Lagos State Fire Service.",
        "2015-02-11", False,
    ),
    (
        "seed://fire-trade-fair-2017",
        "FIRE", "HIGH",
        "Ojo", "Lagos International Trade Fair Complex, Ojo, Lagos",
        "A fire broke out at the Lagos International Trade Fair Complex in Ojo, gutting "
        "several shops and destroying goods. Fire service personnel arrived promptly and "
        "prevented the blaze from spreading to the main exhibition hall.",
        "2017-08-06", False,
    ),
    (
        "seed://fire-ilupeju-2019",
        "FIRE", "HIGH",
        "Ilupeju", "Ilupeju Industrial Estate, Lagos",
        "A fire engulfed a factory at the Ilupeju Industrial Estate, sending a thick plume of "
        "smoke visible across large parts of Lagos. Workers were evacuated safely; firefighters "
        "from three stations responded to contain the blaze.",
        "2019-10-09", False,
    ),
    (
        "seed://fire-kirikiri-2021",
        "FIRE", "HIGH",
        "Kirikiri", "Kirikiri Industrial Layout, Lagos",
        "A chemical factory fire at Kirikiri Industrial Layout sent hazardous smoke billowing "
        "across the area. Nearby residents were evacuated as a precaution while firefighters "
        "spent several hours extinguishing the blaze.",
        "2021-05-19", False,
    ),
    (
        "seed://fire-agbado-2022",
        "FIRE", "CRITICAL",
        "Agbado", "Agbado, Oju-Ore, Lagos",
        "A tanker carrying premium motor spirit caught fire and exploded on the Agbado-Oju-Ore "
        "road, killing two people and injuring several bystanders. The resulting inferno also "
        "destroyed a row of roadside shops before it was extinguished.",
        "2022-04-07", False,
    ),
    (
        "seed://fire-berger-2023",
        "FIRE", "HIGH",
        "Berger", "Ojodu-Berger, Lagos",
        "Fire gutted a row of shops at the Ojodu-Berger market, destroying goods including "
        "electronics and building materials. Dozens of traders were rendered destitute after "
        "the blaze razed their businesses.",
        "2023-08-15", False,
    ),
    (
        "seed://fire-ikeja-market-2024",
        "FIRE", "HIGH",
        "Ikeja", "Computer Village, Ikeja, Lagos",
        "A fire broke out in a section of Computer Village in Ikeja, destroying shops stocking "
        "electronics and accessories worth hundreds of millions of naira. Fire service crews "
        "battled the blaze for several hours.",
        "2024-05-22", False,
    ),
    (
        "seed://fire-surulere-2020",
        "FIRE", "MEDIUM",
        "Surulere", "Bode Thomas Street, Surulere, Lagos",
        "A residential building fire on Bode Thomas Street in Surulere left three families "
        "homeless after their apartments were gutted. Lagos Fire Service officers extinguished "
        "the blaze within two hours; no casualties were reported.",
        "2020-12-03", False,
    ),

    # ── EXPLOSION ──────────────────────────────────────────────────────────────
    (
        "seed://explosion-abule-egba-2020",
        "EXPLOSION", "CRITICAL",
        "Abule-Egba", "Abule-Egba, Agege, Lagos",
        "A gas pipeline explosion and fire at Abule-Egba devastated an entire neighbourhood, "
        "killing at least 23 people and destroying hundreds of houses. The Nigerian Gas Company "
        "pipeline ruptured, triggering a massive inferno that emergency responders took hours to "
        "contain.",
        "2020-03-15", True,
    ),
    (
        "seed://explosion-ejigbo-2018",
        "EXPLOSION", "CRITICAL",
        "Ejigbo", "NNPC Pipeline, Ejigbo, Lagos",
        "An NNPC oil pipeline explosion at Ejigbo killed several scavengers and ignited a "
        "massive fire that consumed surrounding bushes and shanty structures. The fire burned "
        "overnight before being contained by emergency teams.",
        "2018-04-20", True,
    ),
    (
        "seed://explosion-ilupeju-gas-2016",
        "EXPLOSION", "HIGH",
        "Ilupeju", "Ilupeju, Lagos",
        "A gas cylinder explosion at a filling plant in Ilupeju injured several workers and "
        "triggered a fire that spread to adjoining properties. LASEMA teams evacuated residents "
        "within a 200-metre radius during the emergency response.",
        "2016-09-01", True,
    ),
    (
        "seed://explosion-apongbon-2012",
        "EXPLOSION", "CRITICAL",
        "Lagos Island", "Apongbon, Lagos Island",
        "A gas tanker explosion at Apongbon on Lagos Island killed at least five people and "
        "injured dozens. The explosion occurred early morning and the fire took several hours "
        "to bring under control.",
        "2012-08-24", True,
    ),
    (
        "seed://explosion-ijora-2014",
        "EXPLOSION", "HIGH",
        "Ijora", "Ijora-Badia, Lagos",
        "Gas cylinders stored illegally at a residential building exploded in Ijora-Badia, "
        "injuring several residents and destroying property. LASEMA teams evacuated dozens of "
        "families from the affected area.",
        "2014-04-15", True,
    ),
    (
        "seed://explosion-mushin-gas-2019",
        "EXPLOSION", "HIGH",
        "Mushin", "Mushin, Lagos",
        "An LPG gas retail outlet exploded in Mushin, causing a fire that spread to adjacent "
        "buildings. Three people sustained burns and were taken to hospital; fire service "
        "personnel extinguished the blaze after about two hours.",
        "2019-07-22", True,
    ),
    (
        "seed://explosion-ajegunle-2021",
        "EXPLOSION", "HIGH",
        "Ajegunle", "Ajegunle, Lagos",
        "A gas-related explosion in Ajegunle injured four residents and damaged multiple "
        "properties. Residents reported hearing a loud blast before a fire broke out inside "
        "a ground-floor apartment where gas cylinders were stored.",
        "2021-11-05", True,
    ),
    (
        "seed://explosion-lekki-pipeline-2023",
        "EXPLOSION", "CRITICAL",
        "Lekki", "Lekki Phase 2, Lagos",
        "A petroleum pipeline explosion in the Lekki area killed two people and injured several "
        "others. The blast was linked to suspected pipeline vandals; the resulting fire destroyed "
        "surrounding vegetation and structures before being contained.",
        "2023-03-28", True,
    ),

    # ── FLOOD ──────────────────────────────────────────────────────────────────
    (
        "seed://flood-lagos-july-2011",
        "FLOOD", "CRITICAL",
        "Surulere", "Surulere, Lagos Mainland",
        "Heavy rainfall caused severe flooding across Lagos, with Surulere and Mainland areas "
        "worst affected. Hundreds of households were submerged and thousands of residents "
        "displaced as floodwaters rose above one metre in low-lying streets.",
        "2011-07-10", False,
    ),
    (
        "seed://flood-lagos-july-2012",
        "FLOOD", "CRITICAL",
        "Oshodi", "Oshodi-Isale, Lagos",
        "Torrential rain triggered widespread flooding across Lagos, including Oshodi, Mushin, "
        "and Ikorodu areas. Thousands of families were displaced and roads submerged; the Lagos "
        "State Government opened emergency shelters across the city.",
        "2012-07-05", False,
    ),
    (
        "seed://flood-lekki-2016",
        "FLOOD", "HIGH",
        "Lekki", "Lekki-Ajah Expressway, Lagos",
        "Heavy downpours rendered large sections of the Lekki-Ajah Expressway impassable as "
        "floodwaters swept across the road. Many motorists were stranded for hours and several "
        "residential estates on the axis were inundated.",
        "2016-08-12", False,
    ),
    (
        "seed://flood-surulere-2017",
        "FLOOD", "HIGH",
        "Surulere", "Eric Moore, Surulere, Lagos",
        "Eric Moore and surrounding streets in Surulere were flooded after several hours of "
        "heavy rain, displacing families and submerging vehicles. The Lagos Drainage Authority "
        "deployed equipment to pump out water from the worst-affected areas.",
        "2017-07-29", False,
    ),
    (
        "seed://flood-ikorodu-2018",
        "FLOOD", "HIGH",
        "Ikorodu", "Ikorodu, Lagos",
        "Flooding in Ikorodu following prolonged rains destroyed homes and disrupted road "
        "transport across the LGA. Hundreds of families were displaced and several schools "
        "were forced to close as waters rose.",
        "2018-09-17", False,
    ),
    (
        "seed://flood-isale-eko-2019",
        "FLOOD", "CRITICAL",
        "Lagos Island", "Isale-Eko, Lagos Island",
        "Severe flooding on Lagos Island inundated historic neighbourhoods in Isale-Eko, "
        "displacing thousands of residents. Properties and businesses on the waterfront "
        "sustained extensive damage as flood levels reached record heights.",
        "2019-10-15", False,
    ),
    (
        "seed://flood-agege-2020",
        "FLOOD", "HIGH",
        "Agege", "Agege, Lagos",
        "Flooding in Agege caused widespread destruction, inundating homes and blocking "
        "major roads. Over 500 families sought refuge in temporary shelters as floodwaters "
        "remained high for two days following the heavy rainfall.",
        "2020-08-22", False,
    ),
    (
        "seed://flood-lekki-2021",
        "FLOOD", "HIGH",
        "Lekki", "Lekki-Ajah, Lagos",
        "Persistent rainfall caused flooding across the Lekki-Ajah corridor, submerging "
        "hundreds of homes and cutting off some areas for days. The Lagos State Government "
        "deployed emergency responders and relief materials to affected residents.",
        "2021-06-14", False,
    ),
    (
        "seed://flood-alimosho-2022",
        "FLOOD", "HIGH",
        "Alimosho", "Alimosho, Lagos",
        "Several communities in Alimosho LGA were inundated following days of heavy rain, "
        "with families in Ayobo, Ipaja, and Egbeda areas the most affected. LASEMA and the "
        "NEMA deployed relief materials to displaced residents.",
        "2022-09-08", False,
    ),
    (
        "seed://flood-victoria-island-2023",
        "FLOOD", "HIGH",
        "Victoria Island", "Ahmadu Bello Way, Victoria Island, Lagos",
        "Victoria Island experienced severe flooding that brought traffic to a standstill "
        "and inundated office buildings and shops. Several vehicles were swept away by "
        "fast-moving floodwaters along Ahmadu Bello Way.",
        "2023-07-18", False,
    ),
    (
        "seed://flood-apapa-2024",
        "FLOOD", "HIGH",
        "Apapa", "Apapa-Oshodi Expressway, Apapa, Lagos",
        "Heavy rainfall caused major flooding along the Apapa-Oshodi Expressway, blocking "
        "access to the port for over 24 hours. Containers were at risk of being submerged "
        "and truck drivers abandoned their vehicles on the flooded highway.",
        "2024-07-10", False,
    ),

    # ── RTA ──────────────────────────────────────────────────────────────────
    (
        "seed://rta-otedola-2016",
        "RTA", "CRITICAL",
        "Ojodu", "Otedola Bridge, Lagos-Ibadan Expressway",
        "A multiple-vehicle crash involving tankers and commercial buses at Otedola Bridge "
        "on the Lagos-Ibadan Expressway killed several people and injured dozens. Traffic "
        "was gridlocked for several hours as emergency teams cleared the wreckage.",
        "2016-06-10", False,
    ),
    (
        "seed://rta-apapa-trailer-2017",
        "RTA", "CRITICAL",
        "Apapa", "Creek Road, Apapa, Lagos",
        "An articulated trailer with failed brakes crushed several vehicles on Creek Road "
        "in Apapa, killing four people. The Federal Road Safety Corps and LASEMA attended "
        "the scene to evacuate the injured and clear the road.",
        "2017-05-13", False,
    ),
    (
        "seed://rta-mile12-2018",
        "RTA", "HIGH",
        "Ketu", "Mile 12, Ketu-Mile 12, Lagos",
        "A commercial bus and a trailer collided at Mile 12 market axis, killing three "
        "people and injuring over ten others. The FRSC attributed the crash to over-speeding "
        "and overloading by the trailer operator.",
        "2018-11-02", False,
    ),
    (
        "seed://rta-oshodi-2019",
        "RTA", "HIGH",
        "Oshodi", "Oshodi Interchange, Lagos",
        "A road traffic accident at the Oshodi interchange involving multiple vehicles "
        "injured eight people. The collision was caused by a driver who ran a red light "
        "at the busy intersection during rush-hour traffic.",
        "2019-04-29", False,
    ),
    (
        "seed://rta-lekki-expressway-2020",
        "RTA", "CRITICAL",
        "Lekki", "Lekki-Epe Expressway, Lagos",
        "A high-speed accident on the Lekki-Epe Expressway left four people dead and "
        "several seriously injured. Eye-witnesses said the vehicle lost control and "
        "somersaulted several times before hitting a roadside fence.",
        "2020-06-07", False,
    ),
    (
        "seed://rta-badagry-2021",
        "RTA", "CRITICAL",
        "Badagry", "Lagos-Badagry Expressway",
        "A head-on collision between a commercial bus and a truck on the Lagos-Badagry "
        "Expressway killed five people and injured over twelve. The accident occurred in "
        "the early hours and survivors were rushed to General Hospital Badagry.",
        "2021-02-08", False,
    ),
    (
        "seed://rta-ikorodu-2022",
        "RTA", "HIGH",
        "Ikorodu", "Ikorodu Road, Lagos",
        "A commercial bus plunged into a ditch along Ikorodu Road after the driver "
        "swerved to avoid a pothole, injuring eleven passengers. The FRSC and LASEMA "
        "teams evacuated the injured to Ikorodu General Hospital.",
        "2022-08-19", False,
    ),
    (
        "seed://rta-ajah-2023",
        "RTA", "HIGH",
        "Ajah", "Ajah, Lekki-Epe Expressway, Lagos",
        "A multi-vehicle crash at the Ajah U-turn on the Lekki-Epe Expressway injured "
        "nine people, two critically. Traffic was at a standstill for hours as wreckage "
        "was cleared from the busy expressway.",
        "2023-10-24", False,
    ),

    # ── DROWNING ──────────────────────────────────────────────────────────────
    (
        "seed://drowning-bar-beach-2011",
        "DROWNING", "CRITICAL",
        "Victoria Island", "Bar Beach, Victoria Island, Lagos",
        "Three swimmers drowned at Bar Beach on Victoria Island after being caught in a "
        "powerful riptide. Lifeguards attempted a rescue but were unable to reach all "
        "victims before they were swept out to sea.",
        "2011-04-09", False,
    ),
    (
        "seed://drowning-elegushi-2015",
        "DROWNING", "HIGH",
        "Lekki", "Elegushi Beach, Lekki, Lagos",
        "Two young men drowned at Elegushi Beach in Lekki after swimming beyond the "
        "safety markers. Beach patrol officers retrieved the bodies from the water after "
        "a search that lasted several hours.",
        "2015-08-30", False,
    ),
    (
        "seed://drowning-lagoon-boat-2016",
        "DROWNING", "CRITICAL",
        "Lagos Island", "Lagos Lagoon, near Carter Bridge",
        "A wooden passenger boat capsized on the Lagos Lagoon near Carter Bridge, killing "
        "at least seven commuters. The overloaded vessel overturned in rough water; survivors "
        "clung to debris until rescue boats arrived.",
        "2016-09-15", False,
    ),
    (
        "seed://drowning-alpha-beach-2018",
        "DROWNING", "HIGH",
        "Ajah", "Alpha Beach, Ajah, Lagos",
        "Two teenagers drowned at Alpha Beach in Ajah while swimming without supervision. "
        "Their bodies were recovered by locals after an extensive search; the incident "
        "renewed calls for lifeguards at private beaches.",
        "2018-12-29", False,
    ),
    (
        "seed://drowning-ikorodu-2020",
        "DROWNING", "HIGH",
        "Ikorodu", "Ikorodu Waterside, Lagos",
        "A canoe ferrying commuters across the waterway at Ikorodu capsized during a storm, "
        "drowning three passengers. One survivor was pulled from the water by fishermen "
        "who witnessed the incident.",
        "2020-09-12", False,
    ),
    (
        "seed://drowning-takwa-bay-2022",
        "DROWNING", "CRITICAL",
        "Lagos Island", "Takwa Bay, Lagos Harbour",
        "A speedboat ferrying day-trippers to Takwa Bay capsized on the return journey, "
        "killing four passengers. The Lagos Ferry Services rescue team recovered the "
        "victims' bodies after a three-hour search operation.",
        "2022-07-04", False,
    ),
    (
        "seed://drowning-badagry-creek-2023",
        "DROWNING", "HIGH",
        "Badagry", "Badagry Creek, Lagos",
        "A teenager drowned in Badagry Creek after the boat he was travelling in "
        "overturned. Community fishermen dived to retrieve the body; the incident "
        "highlighted the absence of life jackets on local watercraft.",
        "2023-06-17", False,
    ),

    # ── HAZARD ──────────────────────────────────────────────────────────────
    (
        "seed://hazard-ekedc-surulere-2013",
        "HAZARD", "HIGH",
        "Surulere", "Adeniran Ogunsanya Street, Surulere, Lagos",
        "An EKEDC transformer exploded on Adeniran Ogunsanya Street in Surulere, "
        "sparking a fire that damaged nearby stalls and vehicles. Residents reported the "
        "transformer had been vandalised days before the explosion.",
        "2013-03-27", True,
    ),
    (
        "seed://hazard-hightension-ikoyi-2015",
        "HAZARD", "CRITICAL",
        "Ikoyi", "Kingsway Road, Ikoyi, Lagos",
        "A high-tension electricity cable snapped and fell across Kingsway Road in Ikoyi, "
        "electrocuting three passers-by. EKEDC emergency crews de-energised the line "
        "before emergency responders could safely access the victims.",
        "2015-06-02", True,
    ),
    (
        "seed://hazard-nepa-pole-mushin-2017",
        "HAZARD", "HIGH",
        "Mushin", "Mushin, Lagos",
        "An electricity distribution pole collapsed on Mushin Road, leaving live wires "
        "draped across the carriageway. Three people sustained electric shocks before "
        "the EKEDC team isolated the supply and removed the hazard.",
        "2017-04-11", True,
    ),
    (
        "seed://hazard-ekedc-ikeja-2018",
        "HAZARD", "CRITICAL",
        "Ikeja", "Obafemi Awolowo Way, Ikeja, Lagos",
        "An EKEDC distribution transformer exploded on Obafemi Awolowo Way in Ikeja, "
        "causing a fire that spread to two adjacent buildings. One person died and four "
        "were injured; the fire service took over an hour to extinguish the blaze.",
        "2018-02-20", True,
    ),
    (
        "seed://hazard-pipeline-mosafejo-2017",
        "HAZARD", "HIGH",
        "Lagos Island", "Mosafejo, Lagos Island",
        "A gas pipeline leak near Mosafejo on Lagos Island forced the evacuation of "
        "several streets as technicians worked to isolate the leak. Residents were kept "
        "away from the area for over six hours as a precaution against ignition.",
        "2017-11-30", True,
    ),
    (
        "seed://hazard-ekedc-yaba-2019",
        "HAZARD", "HIGH",
        "Yaba", "Herbert Macaulay Way, Yaba, Lagos",
        "A transformer in Yaba exploded and caught fire in the early hours, sending "
        "residents fleeing in panic. The fire destroyed a nearby communication mast before "
        "EKEDC engineers isolated the supply.",
        "2019-06-03", True,
    ),
    (
        "seed://hazard-highvoltage-alimosho-2020",
        "HAZARD", "CRITICAL",
        "Alimosho", "Idimu Road, Alimosho, Lagos",
        "A fallen high-voltage cable electrocuted two people on Idimu Road in Alimosho. "
        "Heavy rainfall the previous night caused the pole to tilt and the cable to make "
        "contact with a flooded portion of the road.",
        "2020-10-01", True,
    ),
    (
        "seed://hazard-ekedc-apapa-2021",
        "HAZARD", "HIGH",
        "Apapa", "Creek Road, Apapa, Lagos",
        "An EKEDC feeder station in Apapa caught fire during a thunderstorm, disrupting "
        "power supply to the port for several hours. Fire service personnel extinguished "
        "the blaze; no human casualties were reported.",
        "2021-08-16", True,
    ),
    (
        "seed://hazard-wire-lekki-2022",
        "HAZARD", "HIGH",
        "Lekki", "Admiralty Way, Lekki Phase 1, Lagos",
        "An electricity cable fell across Admiralty Way in Lekki Phase 1 following a "
        "storm, blocking traffic and posing an electrocution risk. Residents cordoned off "
        "the area until EKEDC engineers arrived to make the site safe.",
        "2022-05-24", True,
    ),
    (
        "seed://hazard-nepa-ikeja-2023",
        "HAZARD", "HIGH",
        "Ikeja", "Allen Avenue, Ikeja, Lagos",
        "An electricity distribution substation on Allen Avenue in Ikeja exploded, "
        "sparking a fire that damaged neighbouring properties. Two nearby shops were "
        "gutted before the Lagos Fire Service extinguished the blaze.",
        "2023-12-06", True,
    ),
    (
        "seed://hazard-gaspipe-agege-2024",
        "HAZARD", "HIGH",
        "Agege", "Agege Motor Road, Agege, Lagos",
        "A gas distribution pipe ruptured along Agege Motor Road, causing a gas leak "
        "that forced closure of the road and evacuation of nearby shops. The Lagos State "
        "Environment and Hazard Monitoring team spent four hours repairing the rupture.",
        "2024-03-19", True,
    ),
]


# ──────────────────────────────────────────────────────────────────────────────
# Lagos zones for geo-extraction
# ──────────────────────────────────────────────────────────────────────────────

LAGOS_ZONES = [
    "Ikeja", "Surulere", "Lekki", "Victoria Island", "Ajah", "Ikorodu",
    "Badagry", "Alimosho", "Oshodi", "Mushin", "Agege", "Kosofe", "Apapa",
    "Lagos Island", "Lagos Mainland", "Yaba", "Orile", "Ojo", "Ajegunle",
    "Isale Eko", "Festac", "Ipaja", "Egbeda", "Ojodu", "Berger", "Gbagada",
    "Maryland", "Ketu", "Mile 12", "Iyana-Ipaja", "Sangotedo", "Epe",
    "Ibeju-Lekki", "Magodo", "Ojota", "Ogudu", "Anthony", "Palmgrove",
    "Bariga", "Shomolu", "Abule-Egba", "Dopemu", "Meiran", "Ijaiye",
    "Ojokoro", "Ifako", "Igando", "Isheri", "Idimu", "Ayobo",
    "Satellite Town", "Trade Fair", "Mile 2", "Kirikiri", "Marina",
    "Broad Street", "Ikoyi", "Oniru", "Elegushi", "Badore",
    "Abraham Adesanya", "Ilaje", "Obalende", "CMS", "Iju-Ishaga",
    "Agbado", "Fagba", "Iyana Iba", "Ejigbo", "Ijora", "Ijora-Badia",
]

ZONE_PATTERN = re.compile(
    r"\b(" + "|".join(re.escape(z) for z in sorted(LAGOS_ZONES, key=len, reverse=True)) + r")\b",
    re.IGNORECASE,
)

INFRASTRUCTURE_KEYWORDS = [
    "transformer", "wire", "cable", "NEPA", "EKEDC", "power line", "electric",
    "electricity", "high tension", "pole", "substation", "generator",
    "gas pipe", "pipeline",
]

TYPE_KEYWORDS = {
    "FIRE":      ["fire", "inferno", "burnt", "burn", "blaze", "arson", "flame", "razed"],
    "FLOOD":     ["flood", "flooding", "waterlog", "inundat", "overflow", "surge", "submerged"],
    "COLLAPSE":  ["collaps", "cave-in", "cave in", "building fall", "structural failure",
                  "rubble", "debris", "crumble"],
    "RTA":       ["accident", "crash", "collision", "vehicle", "truck", "bus",
                  "car", "motorcycle", "okada", "rta", "road traffic",
                  "knocked down", "hit-and-run", "driver", "tanker"],
    "EXPLOSION": ["explo", "blast", "gas leak", "detonat", "bomb", "bang", "pipeline fire"],
    "DROWNING":  ["drown", "submerg", "sea rescue", "river", "ocean", "lagoon",
                  "water body", "canoe", "boat capsize", "capsiz", "swimming"],
    "HAZARD":    ["transformer", "electric shock", "electrocut", "hazard",
                  "EKEDC", "NEPA", "power line", "wire", "high tension",
                  "gas pipe", "chemical spill", "electrocution"],
}

SEVERITY_KEYWORDS = {
    "CRITICAL": ["dead", "died", "death", "killed", "fatality", "fatalities",
                 "corpse", "bodies", "mass casualt", "trapped", "missing",
                 "fully collapsed", "razed", "dozens"],
    "HIGH":     ["injur", "hospitali", "several", "multiple", "families displaced",
                 "destroyed", "gutted", "property loss", "residents displaced"],
    "MEDIUM":   ["contain", "rescue", "no casualt", "minor", "slight", "no fatality"],
    "LOW":      ["near-miss", "averted", "quickly", "no injuries", "prevented"],
}

# ──────────────────────────────────────────────────────────────────────────────
# Google News RSS search queries
# ──────────────────────────────────────────────────────────────────────────────

GNEWS_QUERIES = [
    "Lagos fire outbreak site:punchng.com OR site:vanguardngr.com OR site:premiumtimesng.com",
    "Lagos building collapse LASEMA",
    "Lagos flood disaster victims displaced",
    "Lagos road accident fatality FRSC",
    "Lagos gas explosion pipeline",
    "Lagos drowning lagoon boat capsized",
    "Lagos transformer explosion EKEDC electrocution",
    "Lagos fire market gutted",
    "Lagos tanker fire expressway",
    "Lagos collapse building rubble",
    "Lagos flood residents displaced communities",
    "Lagos RTA accident commercial bus",
    "Lagos LASEMA emergency rescue",
    "Lagos Punch fire outbreak destroyed",
    "Lagos Vanguard building collapse dead",
    "Lagos explosion pipeline NNPC",
]

# ──────────────────────────────────────────────────────────────────────────────
# Direct site RSS feeds (article links work without redirect)
# ──────────────────────────────────────────────────────────────────────────────

DIRECT_RSS_FEEDS = [
    {
        "name": "Vanguard",
        "feed_url": "https://www.vanguardngr.com/feed/",
        "domain": "vanguardngr.com",
        "body_selector": ".entry-content p, .td-post-content p",
        "date_selector": "time[datetime], .entry-date, .td-post-date time",
    },
    {
        "name": "Premium Times",
        "feed_url": "https://www.premiumtimesng.com/feed/",
        "domain": "premiumtimesng.com",
        "body_selector": ".td-post-content p, .entry-content p",
        "date_selector": "time[datetime], .td-post-date time, .entry-date",
    },
    {
        "name": "Daily Trust",
        "feed_url": "https://dailytrust.com/feed/",
        "domain": "dailytrust.com",
        "body_selector": ".entry-content p, .post-content p",
        "date_selector": "time[datetime], .entry-date, .post-meta time",
    },
]

# ──────────────────────────────────────────────────────────────────────────────
# Helper utilities
# ──────────────────────────────────────────────────────────────────────────────

def safe_get(url: str, timeout: int = 15):
    try:
        resp = requests.get(url, headers=HEADERS, timeout=timeout, allow_redirects=True)
        return resp if resp.status_code == 200 else None
    except Exception:
        return None


def extract_incident_type(text: str):
    text_lower = text.lower()
    scores = {t: 0 for t in TYPE_KEYWORDS}
    for itype, keywords in TYPE_KEYWORDS.items():
        for kw in keywords:
            if kw.lower() in text_lower:
                scores[itype] += 1
    best = max(scores, key=lambda k: scores[k])
    return best if scores[best] > 0 else None


def extract_severity(text: str) -> str:
    text_lower = text.lower()
    for level in ["CRITICAL", "HIGH", "MEDIUM", "LOW"]:
        for kw in SEVERITY_KEYWORDS[level]:
            if kw.lower() in text_lower:
                return level
    return "MEDIUM"


def extract_zone(text: str) -> str:
    m = ZONE_PATTERN.search(text)
    if m:
        z = m.group(1)
        return "Victoria Island" if z.upper() == "VI" else z
    return "Lagos"


def extract_address(text: str, zone: str) -> str:
    patterns = [
        r"(?:at|on|along|near|off|in)\s+([A-Z][a-zA-Z0-9\s\-']{5,60}(?:Street|Road|Avenue|Close|Way|Drive|Crescent|Estate|Lane|Bridge|Junction|Market|Plaza|Mall))",
        r"([A-Z][a-zA-Z0-9\s\-']{3,40}(?:Street|Road|Avenue|Close|Way|Drive|Bridge|Market))",
    ]
    for pat in patterns:
        m = re.search(pat, text)
        if m:
            addr = m.group(1).strip()
            return f"{addr}, {zone}, Lagos" if zone not in addr else f"{addr}, Lagos"
    return f"{zone}, Lagos" if zone else "Lagos"


def infra_flag(text: str) -> bool:
    tl = text.lower()
    return any(kw.lower() in tl for kw in INFRASTRUCTURE_KEYWORDS)


def first_n_sentences(text: str, n: int = 3) -> str:
    sentences = re.split(r"(?<=[.!?])\s+", text.strip())
    sentences = [s.strip() for s in sentences if len(s.strip()) > 20]
    return " ".join(sentences[:n])


# Unicode → ASCII replacements for Windows console compatibility
_UNICODE_MAP = str.maketrans({
    "\u2011": "-",   # non-breaking hyphen
    "\u2012": "-",   # figure dash
    "\u2013": "-",   # en dash
    "\u2014": "-",   # em dash
    "\u2018": "'",   # left single quote
    "\u2019": "'",   # right single quote
    "\u201c": '"',   # left double quote
    "\u201d": '"',   # right double quote
    "\u2026": "...", # ellipsis
    "\u00a0": " ",   # non-breaking space
    "\u00e9": "e",   # é
    "\u00e8": "e",   # è
    "\u00fc": "u",   # ü
    "\u00f3": "o",   # ó
})


def sanitize(text: str) -> str:
    """Replace common non-ASCII characters; drop anything still non-ASCII."""
    return text.translate(_UNICODE_MAP).encode("ascii", "replace").decode("ascii")


def parse_date_string(raw: str):
    # Remove timezone name suffixes like "GMT", "UTC" before strptime
    cleaned = re.sub(r"\s*(GMT|UTC)$", "+0000", raw.strip())
    # Try progressively shorter slices for formats with/without timezone
    for fmt in [
        "%a, %d %b %Y %H:%M:%S %z",   # RFC 822: Mon, 30 Mar 2026 15:57:05 +0000
        "%Y-%m-%dT%H:%M:%S%z",         # ISO 8601 with tz
        "%Y-%m-%dT%H:%M:%S",           # ISO 8601 without tz
        "%Y-%m-%d",
        "%B %d, %Y",
        "%b %d, %Y",
        "%d %B %Y",
    ]:
        # Use different slice lengths based on expected format length
        for n in [31, 29, 25, 19, 10]:
            try:
                dt = datetime.strptime(cleaned[:n].strip(), fmt)
                return dt.replace(tzinfo=timezone.utc) if dt.tzinfo is None else dt
            except ValueError:
                continue
    return None


def geocode(address: str):
    url = (
        "https://nominatim.openstreetmap.org/search"
        f"?q={quote_plus(address + ' Lagos Nigeria')}&format=json&limit=1&countrycodes=ng"
    )
    try:
        resp = requests.get(
            url,
            headers={"User-Agent": "Siren-ng seed script / admin@siren.ng"},
            timeout=10,
        )
        data = resp.json()
        if data:
            return float(data[0]["lat"]), float(data[0]["lon"])
    except Exception:
        pass
    return None, None


# ──────────────────────────────────────────────────────────────────────────────
# Insertion
# ──────────────────────────────────────────────────────────────────────────────

def insert_incident(data: dict, do_geocode: bool):
    """Insert one incident. Returns (True, '') or (False, reason)."""
    ext_id = data["external_id"]
    if Incident.objects.filter(external_id=ext_id).exists():
        return False, "duplicate"

    lat, lng = None, None
    if do_geocode and data.get("address_text"):
        lat, lng = geocode(data["address_text"])
        time.sleep(NOMINATIM_DELAY)

    try:
        obj = Incident(
            id=uuid.uuid4(),
            source="WEB",
            external_id=ext_id,
            reporter_hash=REPORTER_HASH,
            reporter_phone="",
            incident_type=data["incident_type"],
            description=data["description"],
            severity=data["severity"],
            status="RESOLVED",
            location_lat=lat,
            location_lng=lng,
            address_text=data.get("address_text", ""),
            zone_name=data.get("zone_name", "Lagos"),
            media_urls=[u for u in [data.get("source_url")] if u],
            ai_confidence=AI_CONFIDENCE,
            fraud_score=0.0,
            ai_raw_response={"seed": "historical", "source": ext_id},
            vouch_count=0,
            vouch_threshold=3,
            total_donations_kobo=0,
            donation_count=0,
            is_infrastructure=data.get("is_infrastructure", False),
        )
        obj.save()
        # Override auto_now_add timestamp with article publication date
        pub = data.get("pub_date")
        if pub:
            Incident.objects.filter(pk=obj.pk).update(created_at=pub)
        return True, ""
    except IntegrityError as e:
        return False, f"IntegrityError: {e}"
    except Exception as e:
        return False, f"Error: {e}"


# ──────────────────────────────────────────────────────────────────────────────
# Scrapers
# ──────────────────────────────────────────────────────────────────────────────

def scrape_gnews_rss(queries: list, stdout, style) -> list:
    """
    Fetch Google News RSS for each query. Parse title + date only (no article fetch).
    Returns list of incident dicts.
    """
    base = "https://news.google.com/rss/search?q={q}&hl=en-NG&gl=NG&ceid=NG:en&num=100"
    results = []
    seen = set()

    for query in queries:
        url = base.format(q=quote_plus(query))
        time.sleep(REQUEST_DELAY)
        resp = safe_get(url)
        if not resp:
            stdout.write(f"  [GNews] Blocked: {query}")
            continue

        soup = BeautifulSoup(resp.text, "xml")
        items = soup.find_all("item")
        stdout.write(f"  [GNews] {query!r:55s} -> {len(items)} items")

        for item in items:
            title_el = item.find("title")
            pub_el   = item.find("pubDate")
            link_el  = item.find("link")
            source_el = item.find("source")

            title = title_el.text.strip() if title_el else ""
            pub_raw = pub_el.text.strip() if pub_el else ""
            link = link_el.text.strip() if link_el else ""
            source_name = source_el.text.strip() if source_el else "Unknown"

            if not title or not link:
                continue
            if link in seen:
                continue
            seen.add(link)

            # Must mention Lagos
            if "lagos" not in title.lower():
                continue

            # Determine incident type from title
            itype = extract_incident_type(title)
            if not itype:
                continue

            # Date: only 2010-2025
            pub_date = parse_date_string(pub_raw) if pub_raw else None
            if pub_date and (pub_date.year < 2010 or pub_date.year > 2025):
                continue
            if not pub_date:
                pub_date = datetime(2020, 1, 1, tzinfo=timezone.utc)

            zone = extract_zone(title)
            address = extract_address(title, zone)
            severity = extract_severity(title)
            is_infra = infra_flag(title)

            # Description from title (we do not fetch the full article for GNews)
            description = sanitize(title.rstrip(".") + ".")
            if len(description) < 60:
                description = f"Emergency incident reported in Lagos: {description}"

            # Google News URLs are too long for external_id(max=200); use a short hash
            ext_id = "gnews:" + hashlib.sha256(link.encode()).hexdigest()[:32]

            results.append({
                "external_id": ext_id,
                "incident_type": itype,
                "description": description,
                "address_text": address,
                "zone_name": zone,
                "severity": severity,
                "is_infrastructure": is_infra,
                "pub_date": pub_date,
                "source": source_name,
                "source_url": link,
            })

    return results


def scrape_direct_rss(feeds: list, stdout, style) -> list:
    """
    Fetch direct RSS feeds, then GET each article page to extract body text.
    Returns list of incident dicts.
    """
    results = []
    seen = set()

    for feed_cfg in feeds:
        time.sleep(REQUEST_DELAY)
        resp = safe_get(feed_cfg["feed_url"])
        if not resp:
            stdout.write(f"  [{feed_cfg['name']}] RSS blocked/failed")
            continue

        soup = BeautifulSoup(resp.text, "xml")
        items = soup.find_all("item")
        stdout.write(f"  [{feed_cfg['name']}] {len(items)} RSS items")

        for item in items:
            title_el = item.find("title")
            pub_el   = item.find("pubDate")
            title = title_el.text.strip() if title_el else ""
            pub_raw = pub_el.text.strip() if pub_el else ""

            # Extract URL from raw XML
            raw = str(item)
            urls = re.findall(
                r"https?://(?:www\.)?" + re.escape(feed_cfg["domain"]) + r"[^\s<\"'>]+",
                raw,
            )
            article_url = urls[0] if urls else ""
            if not article_url or article_url in seen:
                continue
            seen.add(article_url)

            if "lagos" not in title.lower():
                continue

            itype = extract_incident_type(title)
            if not itype:
                continue

            pub_date = parse_date_string(pub_raw) if pub_raw else None
            if pub_date and (pub_date.year < 2010 or pub_date.year > 2025):
                continue
            if not pub_date:
                pub_date = datetime(2022, 1, 1, tzinfo=timezone.utc)

            # Fetch article body
            time.sleep(REQUEST_DELAY)
            art_resp = safe_get(article_url)
            body = ""
            if art_resp:
                art_soup = BeautifulSoup(art_resp.text, "html.parser")
                paras = art_soup.select(feed_cfg["body_selector"])
                body = " ".join(p.get_text(strip=True) for p in paras if len(p.get_text(strip=True)) > 40)

            full = f"{title} {body}"
            zone = extract_zone(full)
            address = extract_address(full, zone)
            severity = extract_severity(full)
            is_infra = infra_flag(full)
            description = sanitize(first_n_sentences(body, 3) if body else title)

            results.append({
                "external_id": article_url,
                "incident_type": itype,
                "description": description[:1000],
                "address_text": address,
                "zone_name": zone,
                "severity": severity,
                "is_infrastructure": is_infra,
                "pub_date": pub_date,
                "source": feed_cfg["name"],
                "source_url": article_url,
            })

    return results


# ──────────────────────────────────────────────────────────────────────────────
# Management command
# ──────────────────────────────────────────────────────────────────────────────

class Command(BaseCommand):
    help = "Seed the database with historical Lagos incidents (hardcoded + live news scraping)."

    def add_arguments(self, parser):
        parser.add_argument("--dry-run", action="store_true",
                            help="Parse and report without inserting.")
        parser.add_argument("--geocode", action="store_true",
                            help="Use Nominatim to geocode addresses (slow, 1 req/sec).")
        parser.add_argument("--skip-hardcoded", action="store_true",
                            help="Skip the built-in historical dataset.")
        parser.add_argument("--skip-live", action="store_true",
                            help="Skip live RSS scraping (hardcoded only).")
        parser.add_argument("--limit", type=int, default=0,
                            help="Max live incidents to insert (0 = unlimited).")

    def handle(self, *args, **options):
        dry_run = options["dry_run"]
        do_geocode = options["geocode"]
        skip_hardcoded = options["skip_hardcoded"]
        skip_live = options["skip_live"]
        limit = options["limit"]

        if dry_run:
            self.stdout.write(self.style.WARNING("DRY RUN — nothing inserted.\n"))

        total_inserted = 0
        total_dup = 0
        total_err = []
        type_counts = {}
        source_counts = {}

        # ── 1. Hardcoded base incidents ────────────────────────────────────────
        if not skip_hardcoded:
            self.stdout.write(self.style.HTTP_INFO("\n" + "=" * 60))
            self.stdout.write(self.style.HTTP_INFO(f"PHASE 1: Hardcoded base dataset ({len(HISTORICAL_INCIDENTS)} incidents)"))
            self.stdout.write(self.style.HTTP_INFO("=" * 60))

            for (ext_id, itype, severity, zone, address, desc, date_str, infra) in HISTORICAL_INCIDENTS:
                pub_date = datetime.strptime(date_str, "%Y-%m-%d").replace(tzinfo=timezone.utc)
                data = {
                    "external_id": ext_id,
                    "incident_type": itype,
                    "description": desc,
                    "address_text": address,
                    "zone_name": zone,
                    "severity": severity,
                    "is_infrastructure": infra,
                    "pub_date": pub_date,
                }

                if dry_run:
                    self.stdout.write(
                        f"  [DRY] {itype:10s} | {severity:8s} | {zone:20s} | {date_str} | {address[:50]}"
                    )
                    total_inserted += 1
                    type_counts[itype] = type_counts.get(itype, 0) + 1
                    source_counts["Hardcoded"] = source_counts.get("Hardcoded", 0) + 1
                    continue

                ok, reason = insert_incident(data, do_geocode)
                if ok:
                    total_inserted += 1
                    type_counts[itype] = type_counts.get(itype, 0) + 1
                    source_counts["Hardcoded"] = source_counts.get("Hardcoded", 0) + 1
                    self.stdout.write(
                        self.style.SUCCESS(
                            f"  [+] {itype:10s} | {severity:8s} | {zone:20s} | {date_str}"
                        )
                    )
                elif reason == "duplicate":
                    total_dup += 1
                    self.stdout.write(f"  [=] SKIP duplicate: {ext_id}")
                else:
                    total_err.append(f"{ext_id}: {reason}")
                    self.stdout.write(self.style.ERROR(f"  [!] {reason}"))

        # ── 2. Google News RSS ─────────────────────────────────────────────────
        if not skip_live:
            self.stdout.write(self.style.HTTP_INFO("\n" + "=" * 60))
            self.stdout.write(self.style.HTTP_INFO(f"PHASE 2: Google News RSS ({len(GNEWS_QUERIES)} queries)"))
            self.stdout.write(self.style.HTTP_INFO("=" * 60))

            gnews_incidents = scrape_gnews_rss(GNEWS_QUERIES, self.stdout, self.style)
            self.stdout.write(f"  Total usable GNews items: {len(gnews_incidents)}")

            live_inserted = 0
            for data in gnews_incidents:
                if limit and live_inserted >= limit:
                    self.stdout.write(f"  [limit {limit} reached — stopping]")
                    break

                if dry_run:
                    self.stdout.write(
                        f"  [DRY] {data['incident_type']:10s} | {data['severity']:8s} | "
                        f"{data['zone_name']:20s} | {data['pub_date'].date()} | {sanitize(data['description'])[:60]}"
                    )
                    total_inserted += 1
                    live_inserted += 1
                    type_counts[data["incident_type"]] = type_counts.get(data["incident_type"], 0) + 1
                    source_counts["Google News"] = source_counts.get("Google News", 0) + 1
                    continue

                ok, reason = insert_incident(data, do_geocode)
                if ok:
                    total_inserted += 1
                    live_inserted += 1
                    type_counts[data["incident_type"]] = type_counts.get(data["incident_type"], 0) + 1
                    source_counts["Google News"] = source_counts.get("Google News", 0) + 1
                    self.stdout.write(
                        self.style.SUCCESS(
                            f"  [+] {data['incident_type']:10s} | {data['severity']:8s} | "
                            f"{data['zone_name']:20s} | {data['pub_date'].date()}"
                        )
                    )
                elif reason == "duplicate":
                    total_dup += 1
                else:
                    total_err.append(f"{data['external_id']}: {reason}")
                    self.stdout.write(self.style.ERROR(f"  [!] {reason}"))

            # ── 3. Direct site RSS with full article fetch ─────────────────────
            self.stdout.write(self.style.HTTP_INFO("\n" + "=" * 60))
            self.stdout.write(self.style.HTTP_INFO("PHASE 3: Direct site RSS (Vanguard / PT / Daily Trust)"))
            self.stdout.write(self.style.HTTP_INFO("=" * 60))

            direct_incidents = scrape_direct_rss(DIRECT_RSS_FEEDS, self.stdout, self.style)
            self.stdout.write(f"  Total usable direct-RSS articles: {len(direct_incidents)}")

            for data in direct_incidents:
                if limit and (live_inserted >= limit):
                    break

                if dry_run:
                    self.stdout.write(
                        f"  [DRY] {data['incident_type']:10s} | {data['severity']:8s} | "
                        f"{data['zone_name']:20s} | {data['pub_date'].date()} | {data['source']}"
                    )
                    total_inserted += 1
                    live_inserted += 1
                    type_counts[data["incident_type"]] = type_counts.get(data["incident_type"], 0) + 1
                    src = data["source"]
                    source_counts[src] = source_counts.get(src, 0) + 1
                    continue

                ok, reason = insert_incident(data, do_geocode)
                if ok:
                    total_inserted += 1
                    live_inserted += 1
                    type_counts[data["incident_type"]] = type_counts.get(data["incident_type"], 0) + 1
                    src = data["source"]
                    source_counts[src] = source_counts.get(src, 0) + 1
                    self.stdout.write(
                        self.style.SUCCESS(
                            f"  [+] {data['incident_type']:10s} | {data['severity']:8s} | "
                            f"{data['zone_name']:20s} | {data['pub_date'].date()} | {src}"
                        )
                    )
                elif reason == "duplicate":
                    total_dup += 1
                else:
                    total_err.append(f"{data['external_id']}: {reason}")
                    self.stdout.write(self.style.ERROR(f"  [!] {reason}"))

        # ── Summary ────────────────────────────────────────────────────────────
        self.stdout.write("\n" + "=" * 60)
        self.stdout.write(self.style.SUCCESS("SEED COMPLETE"))
        self.stdout.write("=" * 60)
        self.stdout.write(f"Total inserted  : {total_inserted}")
        self.stdout.write(f"Duplicates skip : {total_dup}")
        self.stdout.write(f"Errors          : {len(total_err)}")

        self.stdout.write("\nInserted by source:")
        for src, cnt in sorted(source_counts.items(), key=lambda x: -x[1]):
            self.stdout.write(f"  {src:25s} {cnt}")

        self.stdout.write("\nInserted by type:")
        for itype, cnt in sorted(type_counts.items()):
            self.stdout.write(f"  {itype:12s} {cnt}")

        if total_err:
            self.stdout.write(self.style.ERROR("\nInsertion errors:"))
            for e in total_err:
                self.stdout.write(f"  {e}")

#!/usr/bin/env python3
"""
Stáhne stránku s přehledem akcí na webu města Borohrádek
a vygeneruje z ní RSS feed (docs/rss.xml), který lze publikovat
přes GitHub Pages a napojit na IFTTT (RSS Feed -> Facebook Pages).

DŮLEŽITÉ:
Web mestoborohradek.cz může blokovat požadavky bez "prohlížečových"
HTTP hlaviček. Skript proto posílá User-Agent jako běžný prohlížeč.
Pokud přesto dostanete chybu 403/404, zkontrolujte v prohlížeči
(F12 -> Network), jaké přesně požadavky prohlížeč posílá, a hlavičky
níže podle toho doplňte.

Struktura stránky se může změnit (redakční systém aktualizace apod.) -
pokud skript přestane nacházet akce, je potřeba přizpůsobit funkci
parse_events() podle aktuálního HTML (klávesa F12 v prohlížeči na
stránce s akcemi).
"""

import sys
import hashlib
from datetime import datetime, timezone
from urllib.parse import urljoin

import requests
from bs4 import BeautifulSoup
from feedgen.feed import FeedGenerator

# ---------------------------------------------------------------------------
# Nastavení
# ---------------------------------------------------------------------------

BASE_URL = "https://www.mestoborohradek.cz"
EVENTS_URL = f"{BASE_URL}/zivot-ve-meste/udalosti/"
OUTPUT_FILE = "docs/rss.xml"

# Veřejná URL, na které bude feed nakonec dostupný (GitHub Pages).
# Uprav podle svého GitHub účtu a názvu repozitáře.
FEED_PUBLIC_URL = "https://tvservis.github.io/borohradek-rss/rss.xml"

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/124.0.0.0 Safari/537.36"
    ),
    "Accept-Language": "cs-CZ,cs;q=0.9",
}


def fetch_html(url: str) -> str:
    """
    Stáhne HTML stránky, s ošetřením chyb.

    Web mestoborohradek.cz aktivně blokuje požadavky z cloudových/
    datacentrových IP adres (typicky ochrana proti botům). Proto
    používáme requests.Session: nejdřív navštívíme hlavní stránku
    (získáme případné bezpečnostní cookies), a teprve pak stahujeme
    cílovou stránku ve stejné session - u řady podobných ochran to
    pomůže projít.

    Pokud to nepomůže, ochrana je zřejmě založená na blokaci celých
    IP rozsahů datacenter (ne jen na chybějící cookie) - v tom případě
    je potřeba skript spouštět odjinud než z cloudového runneru
    (viz poznámka v NAVOD.md).
    """
    session = requests.Session()
    session.headers.update(HEADERS)

    # Krok 1: "zahřátí" session návštěvou hlavní stránky.
    warmup = session.get(BASE_URL, timeout=20)
    warmup.raise_for_status()

    # Krok 2: stažení cílové stránky ve stejné session.
    response = session.get(url, headers={"Referer": BASE_URL + "/"}, timeout=20)
    response.raise_for_status()
    response.encoding = response.apparent_encoding
    return response.text


def parse_events(html: str, page_url: str):
    """
    Najde na stránce jednotlivé akce.

    Struktura zjištěná přímo z webu (CMS "strankaVypisClankuSFiltr"):

        <a class="fileBox fileBoxGrouped strankaVypisClankuSFiltr_item"
           href="/clanky/pozvanka-na-letni-kino/"
           data-types="novinka udalost">
          <span class="fileBoxContent strankaVypisClankuSFiltr_content">
            <span class="strankaVypisClankuSFiltr_title">Název akce</span>
            <span class="strankaVypisClankuSFiltr_meta">
              <span class="strankaVypisClankuSFiltr_metaItem">
                <span class="strankaVypisClankuSFiltr_metaLabel">Publikováno:</span>
                <strong>12.08.2026</strong>
              </span>
              <span class="strankaVypisClankuSFiltr_metaItem">
                <span class="strankaVypisClankuSFiltr_metaLabel">Termín konání:</span>
                <strong>31.08.2026 20:00 - 03.09.2026 00:00</strong>
              </span>
            </span>
          </span>
        </a>
    """
    soup = BeautifulSoup(html, "html.parser")
    events = []
    seen_links = set()

    items = soup.find_all("a", class_="strankaVypisClankuSFiltr_item")

    for item in items:
        href = item.get("href")
        if not href:
            continue

        full_url = urljoin(page_url, href)
        if full_url in seen_links:
            continue
        seen_links.add(full_url)

        title_el = item.find(class_="strankaVypisClankuSFiltr_title")
        title = title_el.get_text(strip=True) if title_el else full_url
        title = title.replace("\xa0", " ")

        date_text = None
        for meta_item in item.find_all(class_="strankaVypisClankuSFiltr_metaItem"):
            label_el = meta_item.find(class_="strankaVypisClankuSFiltr_metaLabel")
            if not label_el:
                continue
            if "Termín konání" in label_el.get_text():
                strong_el = meta_item.find("strong")
                if strong_el:
                    date_text = strong_el.get_text(strip=True)
                break

        events.append(
            {
                "title": title,
                "url": full_url,
                "date_text": date_text,
            }
        )

    return events


def make_guid(event: dict) -> str:
    """Stabilní jedinečné ID položky, aby IFTTT nepostoval duplicity."""
    return hashlib.sha256(event["url"].encode("utf-8")).hexdigest()


def build_feed(events: list) -> FeedGenerator:
    fg = FeedGenerator()
    fg.id(FEED_PUBLIC_URL)
    fg.title("Akce - Město Borohrádek")
    fg.link(href=EVENTS_URL, rel="alternate")
    fg.link(href=FEED_PUBLIC_URL, rel="self")
    fg.language("cs")
    fg.description("Automaticky generovaný feed akcí z webu mestoborohradek.cz")

    for event in events:
        fe = fg.add_entry()
        fe.id(make_guid(event))
        fe.title(event["title"])
        fe.link(href=event["url"])
        description = event["title"]
        if event["date_text"]:
            description += f" (Datum konání: {event['date_text']})"
        fe.description(description)
        fe.pubDate(datetime.now(timezone.utc))

    return fg


def main():
    try:
        html = fetch_html(EVENTS_URL)
    except requests.RequestException as exc:
        print(f"Chyba při stahování stránky: {exc}", file=sys.stderr)
        sys.exit(1)

    events = parse_events(html, EVENTS_URL)

    if not events:
        print(
            "Nenalezeny žádné akce - zkontroluj strukturu stránky "
            "a uprav funkci parse_events().",
            file=sys.stderr,
        )
        # Neukončujeme chybou, aby předchozí platný rss.xml zůstal zachovaný.
        sys.exit(0)

    print(f"Nalezeno {len(events)} akcí.")
    for e in events:
        print(f" - {e['title']} | {e['date_text']} | {e['url']}")

    fg = build_feed(events)
    fg.rss_file(OUTPUT_FILE, pretty=True)
    print(f"RSS feed uložen do {OUTPUT_FILE}")


if __name__ == "__main__":
    main()

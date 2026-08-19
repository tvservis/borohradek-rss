# Návod – automatické RSS z webu města Borohrádek → Facebook (IFTTT)

## Co to dělá

1. `generate_rss.py` stáhne stránku `https://www.mestoborohradek.cz/prehled-akci`
   a vygeneruje `docs/rss.xml`.
2. GitHub Actions (`.github/workflows/generate-rss.yml`) spouští skript
   automaticky každou hodinu a výsledek commitne zpět do repozitáře.
3. GitHub Pages zveřejní `docs/rss.xml` na veřejné URL.
4. IFTTT applet „RSS Feed → Facebook Pages" sleduje tuto URL a nové akce
   automaticky postuje na Facebook stránku města.

## Krok 1 – Založení GitHub repozitáře

1. Na https://github.com vytvořte nový **veřejný** repozitář, např. `borohradek-rss`.
   (Musí být veřejný, aby fungovaly GitHub Pages zdarma.)
2. Nahrajte do něj obsah této složky (`generate_rss.py`, `requirements.txt`,
   `.github/workflows/generate-rss.yml`, `docs/` – klidně i prázdnou).

   Přes příkazovou řádku:
   ```bash
   git init
   git add .
   git commit -m "Initial commit"
   git branch -M main
   git remote add origin https://github.com/TVE_GH_JMENO/borohradek-rss.git
   git push -u origin main
   ```

## Krok 2 – Úprava FEED_PUBLIC_URL ve skriptu

V souboru `generate_rss.py` najděte řádek:
```python
FEED_PUBLIC_URL = "https://TVE_GH_JMENO.github.io/borohradek-rss/rss.xml"
```
a nahraďte `TVE_GH_JMENO` svým GitHub uživatelským jménem (a případně
upravte i název repozitáře, pokud se liší od `borohradek-rss`).

## Krok 3 – Zapnutí GitHub Pages

1. V repozitáři jděte do **Settings → Pages**.
2. U „Build and deployment" zvolte **Deploy from a branch**.
3. Branch: `main`, složka: **/docs**.
4. Uložte. Za pár desítek sekund bude feed dostupný na:
   ```
   https://TVE_GH_JMENO.github.io/borohradek-rss/rss.xml
   ```
   (Funguje až po prvním úspěšném běhu workflow, který soubor vytvoří.)

## Krok 4 – Ruční spuštění a kontrola

1. V repozitáři na GitHubu klikněte na záložku **Actions**.
2. Vyberte workflow „Generuj RSS feed akcí".
3. Klikněte **Run workflow** (tlačítko vpravo) pro ruční první spuštění.
4. Po doběhnutí zkontrolujte, že v `docs/rss.xml` přibyl obsah, a že
   je dostupný na výše uvedené GitHub Pages URL v prohlížeči.

⚠️ Pokud workflow selže s chybou "Nenalezeny žádné akce" nebo s chybou
stahování stránky – nejspíš bude potřeba upravit selektory ve funkci
`parse_events()` podle aktuální struktury webu (viz komentáře ve skriptu).
V tom případě mi pošlete chybovou hlášku z Actions logu, pomůžu to doladit.

## Krok 5 – Napojení na IFTTT

1. Na https://ifttt.com vytvořte nový applet.
2. **If This** → služba **RSS Feed** → trigger **New feed item**.
3. Vložte URL feedu: `https://TVE_GH_JMENO.github.io/borohradek-rss/rss.xml`
4. **Then That** → služba **Facebook Pages** → akce **Create link post**
   (propojte s Facebook stránkou města, pokud ještě není).
5. Text zprávy např.:
   ```
   {{EntryTitle}}

   {{EntryUrl}}
   ```
6. Uložte a applet zapněte.

## Údržba

- Interval spouštění (`cron`) lze upravit v `.github/workflows/generate-rss.yml`.
- Pokud město změní vzhled webu, bude nejspíš potřeba upravit
  `parse_events()` v `generate_rss.py`.

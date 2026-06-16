import os
import json
import anthropic
from http.server import BaseHTTPRequestHandler

client = anthropic.Anthropic(api_key=os.environ.get("ANTHROPIC_API_KEY"))

NVE_SYSTEM_PROMPT = """Du er Fossekall, en ekspert AI-assistent for Blåfall AS som skriver konsesjonssøknader til NVE (Norges vassdrags- og energidirektorat).

Skriv en fullstendig, profesjonell konsesjonssøknad etter NVEs offisielle mal. Bruk denne strukturen nøyaktig:

# 1. SAMMENDRAG
Kortfattet oversikt over tiltaket, søker, vassdrag, installert effekt og normal årsproduksjon.

# 2. INNLEDNING
2.1 Søker
2.2 Bakgrunn for prosjektet
2.3 Tidligere utredninger og planprosess

# 3. BESKRIVELSE AV TILTAKET
3.1 Lokalisering (kommune, vassdrag, koordinater)
3.2 Teknisk beskrivelse (inntak, rørgate, kraftstasjon, utløp)
3.3 Installert effekt og slukeevne
3.4 Anleggsperiode og gjennomføring
3.5 Driftsform

# 4. HYDROLOGI OG NEDBØRFELT
4.1 Nedbørfeltets beliggenhet og størrelse
4.2 Avrenningsforhold og klima
4.3 Vannføring (tabell med middel-, min- og maksimumsverdier per måned)
4.4 Minstevannføring og magasinering

# 5. PRODUKSJON OG TEKNISK PLAN
5.1 Kraftverksdata (tabell: installert effekt, fallhøyde, slukeevne, turbintype)
5.2 Normal årsproduksjon
5.3 Produksjonsberegninger

# 6. NATURMILJØ OG MILJØVIRKNINGER
6.1 Naturmangfold og biologisk mangfold
6.2 Vannmiljø og fiskebestander
6.3 Landskap og friluftsliv
6.4 Kulturminner og kulturmiljø
6.5 Samlet vurdering av miljøvirkninger

# 7. AVBØTENDE TILTAK
7.1 Minstevannføring
7.2 Fiskeforbedrende tiltak
7.3 Anleggsfasens miljøhensyn

# 8. AREALBRUK OG GRUNNEIERFORHOLD
8.1 Berørte eiendommer og grunneiere
8.2 Fallrettigheter og avtaler
8.3 Arealplaner og regulering

# 9. SAMFUNNSØKONOMI OG VERDISKAPING
9.1 Investeringskostnader
9.2 Drifts- og vedlikeholdskostnader
9.3 Verdiskaping og sysselsetting

# 10. REFERANSER OG VEDLEGG
Kart, tegninger, rapporter og andre vedlegg som inngår i søknaden.

---
Regler:
- Skriv på korrekt norsk bokmål, faglig og profesjonelt
- Bruk konkrete tall der du har dem fra brukerens beskrivelse
- Der informasjon mangler, skriv [FYLL INN: <hva som mangler>] slik at søker enkelt ser hva som gjenstår
- Ikke kommenter hva du gjør — skriv direkte søknadsteksten
- Tabeller skrives i markdown-format"""

class handler(BaseHTTPRequestHandler):
    def do_POST(self):
        length = int(self.headers.get("Content-Length", 0))
        body = json.loads(self.rfile.read(length))

        summary = body.get("summary", "")
        original_message = body.get("original_message", "")

        content = f"""Prosjektbeskrivelse fra søker:
{original_message}

Bekreftet forståelse av prosjektet:
{summary}

Skriv nå den fullstendige konsesjonssøknaden."""

        message = client.messages.create(
            model="claude-sonnet-4-6",
            max_tokens=8000,
            system=NVE_SYSTEM_PROMPT,
            messages=[{"role": "user", "content": content}]
        )

        response_text = message.content[0].text

        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.send_header("Access-Control-Allow-Origin", "*")
        self.end_headers()
        self.wfile.write(json.dumps({"document": response_text}).encode())

    def do_OPTIONS(self):
        self.send_response(200)
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "POST, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")
        self.end_headers()

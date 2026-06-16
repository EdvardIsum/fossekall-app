import os
import json
import anthropic
from http.server import BaseHTTPRequestHandler

client = anthropic.Anthropic(api_key=os.environ.get("ANTHROPIC_API_KEY"))

SYSTEM_PROMPT = """Du er Fossekall, en AI-assistent som hjelper Blåfall AS med å skrive konsesjonssøknader til NVE.

Når du mottar informasjon fra brukeren, skal du skrive en kort og presis oppsummering av hva du har forstått.
Strukturer oppsummeringen slik:
- Prosjektnavn og lokasjon
- Type tiltak (elvekraftverk, pumpekraftverk, etc.)
- Nøkkeltall du har fått (effekt, produksjon, fallhøyde, etc.)
- Vedlagte dokumenter
- Hva som mangler eller er uklart

Skriv på norsk. Vær konkret og tydelig. Avslutt med å spørre om oppsummeringen stemmer."""

class handler(BaseHTTPRequestHandler):
    def do_POST(self):
        length = int(self.headers.get("Content-Length", 0))
        body = json.loads(self.rfile.read(length))

        user_message = body.get("message", "")
        filenames = body.get("filenames", [])

        content = user_message
        if filenames:
            content += f"\n\nVedlagte filer: {', '.join(filenames)}"

        message = client.messages.create(
            model="claude-sonnet-4-6",
            max_tokens=1024,
            system=SYSTEM_PROMPT,
            messages=[{"role": "user", "content": content}]
        )

        response_text = message.content[0].text

        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.send_header("Access-Control-Allow-Origin", "*")
        self.end_headers()
        self.wfile.write(json.dumps({"summary": response_text}).encode())

    def do_OPTIONS(self):
        self.send_response(200)
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "POST, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")
        self.end_headers()

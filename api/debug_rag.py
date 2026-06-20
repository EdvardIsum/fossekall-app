import os
import json
from http.server import BaseHTTPRequestHandler


class handler(BaseHTTPRequestHandler):
    def do_POST(self):
        try:
            length = int(self.headers.get("Content-Length", 0))
            body = json.loads(self.rfile.read(length))

            query = body.get("query", "").strip()
            dokumenttype = body.get("dokumenttype") or None
            antall = int(body.get("antall", 4))

            if not query:
                self._json(400, {"error": "Mangler 'query' i request body"})
                return

            import voyageai
            from supabase import create_client

            voyage = voyageai.Client(api_key=os.environ["VOYAGE_API_KEY"])
            supabase = create_client(
                os.environ["SUPABASE_URL"],
                os.environ["SUPABASE_SECRET_KEY"]
            )

            embedding_result = voyage.embed([query], model="voyage-3", input_type="query")
            embedding = embedding_result.embeddings[0]

            params = {"query_embedding": embedding, "match_count": antall}
            if dokumenttype:
                params["filter_dokumenttype"] = dokumenttype

            response = supabase.rpc("match_dokumenter", params).execute()
            rader = response.data or []

            resultater = [
                {
                    "prosjekt": r.get("prosjekt"),
                    "firma": r.get("firma"),
                    "dokumenttype": r.get("dokumenttype"),
                    "similarity": round(r.get("similarity", 0), 4),
                    "avsnitt_tekst": r.get("avsnitt_tekst"),
                }
                for r in rader
            ]

            self._json(200, {
                "query": query,
                "antall_treff": len(resultater),
                "resultater": resultater,
            })

        except Exception as e:
            self._json(500, {"error": str(e)})

    def do_OPTIONS(self):
        self.send_response(200)
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "POST, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")
        self.end_headers()

    def _json(self, status, data):
        payload = json.dumps(data, ensure_ascii=False).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Access-Control-Allow-Origin", "*")
        self.end_headers()
        self.wfile.write(payload)

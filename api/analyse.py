import json
import math
import os
import requests
from datetime import date
from http.server import BaseHTTPRequestHandler

NVE_API_KEY = os.getenv("NVE_API_KEY")

KVALITET = {1: "Svart høy", 2: "Høy", 3: "Moderat", 4: "Lav", 5: "Svart lav"}
TILSTAND = {1: "Svart god", 2: "God", 3: "Moderat", 4: "Dårlig", 5: "Svart dårlig"}


def _haversine_km(lat1, lon1, lat2, lon2):
    R = 6371
    dl = math.radians(lat2 - lat1)
    dm = math.radians(lon2 - lon1)
    a = math.sin(dl / 2) ** 2 + math.cos(math.radians(lat1)) * math.cos(math.radians(lat2)) * math.sin(dm / 2) ** 2
    return R * 2 * math.asin(math.sqrt(a))


def _til_mercator(lon, lat):
    x = lon * 20037508.34 / 180
    y = math.log(math.tan((90 + lat) * math.pi / 360)) * (180 / math.pi)
    return x, y * 20037508.34 / 180


def _bbox(lat, lon, radius_km):
    dlat = radius_km / 111.0
    dlon = radius_km / (111.0 * math.cos(math.radians(lat)))
    return dlat, dlon


def hent_nve(lat, lon, radius_km=50):
    if not NVE_API_KEY:
        return {"ok": False, "feil": "Ingen NVE_API_KEY konfigurert"}
    try:
        r = requests.get(
            "https://hydapi.nve.no/api/v1/Stations",
            headers={"X-API-Key": NVE_API_KEY},
            params={"Active": "OnlyActive"},
            timeout=15,
        )
        r.raise_for_status()
        alle = r.json().get("data", [])

        naere = []
        for s in alle:
            s_lat = s.get("latitude")
            s_lon = s.get("longitude")
            if s_lat is None or s_lon is None:
                continue
            dist = _haversine_km(lat, lon, s_lat, s_lon)
            if dist <= radius_km:
                s["_dist_km"] = round(dist, 1)
                naere.append(s)
        naere.sort(key=lambda x: x["_dist_km"])

        if not naere:
            return {"ok": False, "feil": f"Ingen stasjoner innen {radius_km} km"}

        ar_fra = date.today().year - 10
        ref_time = f"{ar_fra}-01-01/{date.today().isoformat()}"

        for kandidat in naere[:15]:
            sr = requests.get(
                "https://hydapi.nve.no/api/v1/Observations",
                headers={"X-API-Key": NVE_API_KEY},
                params={
                    "StationId": kandidat.get("stationId"),
                    "Parameter": "1001",
                    "ResolutionTime": "1440",
                    "ReferenceTime": ref_time,
                },
                timeout=20,
            )
            if sr.ok:
                serie = sr.json().get("data", [])
                if serie:
                    obs = serie[0].get("observations", [])
                    verdier = sorted([o["value"] for o in obs if o.get("value") is not None])
                    if verdier:
                        mq = sum(verdier) / len(verdier)
                        m95 = verdier[int(len(verdier) * 0.05)]
                        return {
                            "ok": True,
                            "stasjon_navn": kandidat.get("stationName"),
                            "stasjon_id": kandidat.get("stationId"),
                            "vassdrag": kandidat.get("riverName", ""),
                            "avstand_km": kandidat["_dist_km"],
                            "mq_m3s": round(mq, 3),
                            "m95_m3s": round(m95, 3),
                            "min_m3s": round(verdier[0], 3),
                            "maks_m3s": round(verdier[-1], 3),
                            "antall_dagsverdier": len(verdier),
                        }

        return {"ok": False, "feil": "Ingen vannføringsstasjon funnet blant de 15 nærmeste"}

    except Exception as e:
        return {"ok": False, "feil": str(e)}


def hent_rodlistede(lat, lon, radius_km=10):
    dlat, dlon = _bbox(lat, lon, radius_km)
    x_min, y_min = _til_mercator(lon - dlon, lat - dlat)
    x_max, y_max = _til_mercator(lon + dlon, lat + dlat)
    wkt = (
        f"POLYGON(({x_min:.0f} {y_min:.0f},"
        f"{x_max:.0f} {y_min:.0f},"
        f"{x_max:.0f} {y_max:.0f},"
        f"{x_min:.0f} {y_max:.0f},"
        f"{x_min:.0f} {y_min:.0f}))"
    )
    try:
        r = requests.get(
            "https://artskart.artsdatabanken.no/publicapi/api/observations/list",
            params=[
                ("filter.wktPolygon", wkt),
                ("filter.status[]", "CR"),
                ("filter.status[]", "EN"),
                ("filter.status[]", "VU"),
                ("filter.status[]", "NT"),
                ("pageSize", 100),
            ],
            timeout=20,
        )
        r.raise_for_status()
        data = r.json()
        funn = data.get("Observations", [])
        totalt = data.get("TotalCount", len(funn))

        arter = {}
        for f in funn:
            vitenskapelig = f.get("ScientificName") or f.get("scientificName") or "ukjent"
            norsk = f.get("Name") or f.get("vernacularName") or ""
            kategori = f.get("Status") or f.get("redlistCategory") or "?"
            if vitenskapelig not in arter:
                arter[vitenskapelig] = {"norsk": norsk, "kategori": kategori, "antall": 0}
            arter[vitenskapelig]["antall"] += 1

        kat_orden = {"CR": 0, "EN": 1, "VU": 2, "NT": 3, "DD": 4}
        sortert = sorted(
            [{"vitenskapelig": k, **v} for k, v in arter.items()],
            key=lambda x: kat_orden.get(x["kategori"], 9),
        )
        return {"totalt": totalt, "arter": sortert}

    except Exception as e:
        return {"totalt": 0, "arter": [], "feil": str(e)}


def hent_naturtyper(lat, lon, radius_km=5):
    dlat, dlon = _bbox(lat, lon, radius_km)
    bbox = f"{lon - dlon},{lat - dlat},{lon + dlon},{lat + dlat}"
    try:
        r = requests.get(
            "https://kart.miljodirektoratet.no/arcgis/rest/services/naturtyper_nin/MapServer/0/query",
            params={
                "geometry": bbox,
                "geometryType": "esriGeometryEnvelope",
                "inSR": "4326",
                "spatialRel": "esriSpatialRelIntersects",
                "outFields": "*",
                "returnGeometry": "false",
                "resultRecordCount": 50,
                "f": "json",
            },
            timeout=15,
        )
        r.raise_for_status()
        data = r.json()
        if "error" in data:
            return {"lokaliteter": [], "feil": data["error"].get("message", "API-feil")}

        lokaliteter = []
        for f in data.get("features", []):
            a = f.get("attributes", {})
            kval_int = a.get("Lokalitetskvalitet")
            tilstand_int = a.get("Tilstand")
            lokaliteter.append({
                "navn": a.get("Områdenavn") or a.get("Naturtype") or "ukjent",
                "type": a.get("Naturtype") or "",
                "kvalitet_tekst": KVALITET.get(kval_int, "") if kval_int else "",
                "kvalitet_int": kval_int or 0,
                "tilstand_tekst": TILSTAND.get(tilstand_int, "") if tilstand_int else "",
            })
        return {"lokaliteter": lokaliteter}

    except Exception as e:
        return {"lokaliteter": [], "feil": str(e)}


def beregn_produksjon(fallhoyde_m, nedborfelt_km2, lat):
    if lat > 63:
        avrenning_mm, region = 1500, "Nord-Norge"
    elif lat > 62:
        avrenning_mm, region = 2000, "Midt-Norge"
    elif lat > 60:
        avrenning_mm, region = 2500, "Vestlandet"
    else:
        avrenning_mm, region = 1800, "Østlandet/Sørlandet"

    areal_m2 = nedborfelt_km2 * 1_000_000
    mq = (avrenning_mm / 1000 * areal_m2) / (365.25 * 24 * 3600)
    alv = mq * 0.12
    slukeevne = alv * 4
    eta = 0.88
    effekt_kw = 1000 * 9.81 * slukeevne * fallhoyde_m * eta / 1000
    produksjon_gwh = effekt_kw * 5500 / 1_000_000

    if effekt_kw / 1000 < 0.1:
        kategori = "Mikrokraft (< 0,1 MW)"
    elif effekt_kw / 1000 < 1:
        kategori = "Minikraft (0,1–1 MW)"
    elif effekt_kw / 1000 < 10:
        kategori = "Småkraft (1–10 MW)"
    else:
        kategori = "Middelskraft (> 10 MW)"

    return {
        "fallhoyde_m": fallhoyde_m,
        "nedborfelt_km2": nedborfelt_km2,
        "region": region,
        "avrenning_mm": avrenning_mm,
        "mq_ls": round(mq * 1000),
        "alv_ls": round(alv * 1000),
        "slukeevne_ls": round(slukeevne * 1000),
        "installert_effekt_mw": round(effekt_kw / 1000, 2),
        "produksjon_gwh": round(produksjon_gwh, 1),
        "kategori": kategori,
    }


class handler(BaseHTTPRequestHandler):
    def do_OPTIONS(self):
        self.send_response(200)
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "POST, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")
        self.end_headers()

    def do_POST(self):
        try:
            length = int(self.headers.get("Content-Length", 0))
            body = json.loads(self.rfile.read(length))

            lat = float(body.get("lat", 0))
            lon = float(body.get("lon", 0))
            fallhoyde_m = float(body.get("fallhoyde_m", 0))
            nedborfelt_km2 = float(body.get("nedborfelt_km2", 0))
            radius_km = int(body.get("radius_km", 10))

            # Formater dato på norsk
            mnd = ["januar","februar","mars","april","mai","juni",
                   "juli","august","september","oktober","november","desember"]
            d = date.today()
            dato_norsk = f"{d.day}. {mnd[d.month - 1]} {d.year}"

            resultat = {
                "prosjekt": {
                    "navn": body.get("vassdrag_navn", ""),
                    "soker": body.get("soker", ""),
                    "dato": dato_norsk,
                    "kommune": body.get("kommune", ""),
                    "fylke": body.get("fylke", ""),
                    "vassdrag": body.get("vassdrag_navn", ""),
                    "lat": lat,
                    "lon": lon,
                },
                "hydrologi": hent_nve(lat, lon),
                "biologi": {
                    **hent_rodlistede(lat, lon, radius_km),
                    "naturtyper": hent_naturtyper(lat, lon, radius_km)["lokaliteter"],
                    "radius_km": radius_km,
                },
                "produksjon": beregn_produksjon(fallhoyde_m, nedborfelt_km2, lat),
            }

            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.send_header("Access-Control-Allow-Origin", "*")
            self.end_headers()
            self.wfile.write(json.dumps(resultat, ensure_ascii=False).encode("utf-8"))

        except Exception as e:
            self.send_response(500)
            self.send_header("Content-Type", "application/json")
            self.send_header("Access-Control-Allow-Origin", "*")
            self.end_headers()
            self.wfile.write(json.dumps({"error": str(e)}).encode())

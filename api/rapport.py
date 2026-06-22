import json
from http.server import BaseHTTPRequestHandler

# Fargekoder for rødlistekategorier
_KAT_STIL = {
    "CR": ("background:#f3d8d8;color:#9a2f2f", "CR · Kritisk truet"),
    "EN": ("background:#f3d8d8;color:#9a2f2f", "EN · Sterkt truet"),
    "VU": ("background:#f3e3d8;color:#a84a23", "VU · Sårbar"),
    "NT": ("background:#f0ecd9;color:#897619", "NT · Nær truet"),
    "DD": ("background:#efefef;color:#555",    "DD · Datamangel"),
}

# Kvalitetsnivå → badge-stil (A/B/C)
_KVAL_STIL = {
    1: ("background:#2f6b73;color:#fff", "A · Svært viktig"),
    2: ("background:#5a7355;color:#fff", "B · Viktig"),
    3: ("background:#8a9499;color:#fff", "C · Registrert"),
    4: ("background:#8a9499;color:#fff", "C · Registrert"),
    5: ("background:#8a9499;color:#fff", "C · Registrert"),
}


def _art_rader(arter):
    if not arter:
        return '<tr><td colspan="4" style="padding:14px 0;color:#8a9499;font-size:13px;">Ingen rødlistede arter registrert i influensområdet.</td></tr>'
    rader = []
    for a in arter:
        kat = a.get("kategori", "?")
        stil, etikett = _KAT_STIL.get(kat, ("background:#eee;color:#333", kat))
        norsk = a.get("norsk", "")
        vitenskap = a.get("vitenskapelig", "")
        antall = a.get("antall", 0)
        rader.append(f"""
            <tr style="border-bottom:1px solid #ece9e1;">
              <td style="padding:11px 8px 11px 0;font-weight:500;">{norsk}</td>
              <td style="padding:11px 8px;font-style:italic;color:#5b6a6e;">{vitenskap}</td>
              <td style="padding:11px 8px;text-align:center;">
                <span style="display:inline-block;{stil};font-size:11.5px;font-weight:600;padding:2px 8px;border-radius:3px;">{etikett}</span>
              </td>
              <td style="padding:11px 0 11px 8px;text-align:right;font-variant-numeric:tabular-nums;">{antall}</td>
            </tr>""")
    return "\n".join(rader)


def _naturtype_kort(lokaliteter):
    if not lokaliteter:
        return '<p style="font-size:13px;color:#8a9499;margin:0;">Ingen naturtyper registrert i influensområdet.</p>'
    kort = []
    for lok in lokaliteter[:12]:
        kval_int = lok.get("kvalitet_int", 0)
        if kval_int in _KVAL_STIL:
            badge_stil, badge_tekst = _KVAL_STIL[kval_int]
        else:
            badge_stil, badge_tekst = "background:#efefef;color:#555", ""
        navn = lok.get("navn", "ukjent")
        naturtype = lok.get("type", "")
        badge_html = f'<span style="flex:none;{badge_stil};font-size:11px;font-weight:600;padding:2px 8px;border-radius:3px;">{badge_tekst}</span>' if badge_tekst else ""
        kort.append(f"""
          <div style="border:1px solid #dfdcd3;border-radius:2px;padding:14px 16px;">
            <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:6px;gap:8px;">
              <span style="font-size:14px;font-weight:600;color:#1c2a2e;">{navn}</span>
              {badge_html}
            </div>
            <div style="font-size:12.5px;color:#6b7a7e;">{naturtype}</div>
          </div>""")
    return "\n".join(kort)


def _fmt(verdi, desimaler=2):
    """Formater tall med norsk komma."""
    if verdi is None:
        return "–"
    return f"{verdi:,.{desimaler}f}".replace(",", " ").replace(".", ",").replace(" ", ".")


def bygg_html(data):
    p = data.get("prosjekt", {})
    h = data.get("hydrologi", {})
    b = data.get("biologi", {})
    pr = data.get("produksjon", {})

    # Hydrologi-visning
    if h.get("ok"):
        hydrologi_stasjon_html = f"""
        <div style="display:flex;align-items:center;gap:16px;background:#eef3f2;padding:14px 20px;border-radius:2px;margin-bottom:18px;">
          <div style="flex:1;">
            <div style="font-size:10.5px;letter-spacing:.1em;text-transform:uppercase;color:#5b8a8e;margin-bottom:4px;">Nærmeste NVE-stasjon</div>
            <div style="font-size:16px;font-weight:600;color:#1c2a2e;">{h.get("stasjon_id","")} {h.get("stasjon_navn","")}</div>
          </div>
          <div style="width:1px;align-self:stretch;background:#cfddd9;"></div>
          <div style="text-align:right;">
            <div style="font-size:10.5px;letter-spacing:.1em;text-transform:uppercase;color:#5b8a8e;margin-bottom:4px;">Avstand</div>
            <div style="font-size:16px;font-weight:600;color:#1c2a2e;">{_fmt(h.get("avstand_km"),1)} km</div>
          </div>
        </div>
        <div style="display:grid;grid-template-columns:repeat(4,1fr);gap:12px;">
          <div style="border-top:2px solid #2f6b73;padding-top:10px;">
            <div style="font-size:10.5px;letter-spacing:.06em;text-transform:uppercase;color:#8a9499;margin-bottom:6px;">MQ · Middelvannføring</div>
            <div style="font-family:'Newsreader',serif;font-size:27px;font-weight:500;color:#1c2a2e;line-height:1;">{_fmt(h.get("mq_m3s"),3)}<span style="font-size:14px;color:#6b7a7e;font-family:'IBM Plex Sans';margin-left:3px;">m³/s</span></div>
          </div>
          <div style="border-top:2px solid #2f6b73;padding-top:10px;">
            <div style="font-size:10.5px;letter-spacing:.06em;text-transform:uppercase;color:#8a9499;margin-bottom:6px;">M95 · Lavvannføring</div>
            <div style="font-family:'Newsreader',serif;font-size:27px;font-weight:500;color:#1c2a2e;line-height:1;">{_fmt(h.get("m95_m3s"),3)}<span style="font-size:14px;color:#6b7a7e;font-family:'IBM Plex Sans';margin-left:3px;">m³/s</span></div>
          </div>
          <div style="border-top:2px solid #c4cbc8;padding-top:10px;">
            <div style="font-size:10.5px;letter-spacing:.06em;text-transform:uppercase;color:#8a9499;margin-bottom:6px;">Min. observert</div>
            <div style="font-family:'Newsreader',serif;font-size:27px;font-weight:500;color:#1c2a2e;line-height:1;">{_fmt(h.get("min_m3s"),3)}<span style="font-size:14px;color:#6b7a7e;font-family:'IBM Plex Sans';margin-left:3px;">m³/s</span></div>
          </div>
          <div style="border-top:2px solid #c4cbc8;padding-top:10px;">
            <div style="font-size:10.5px;letter-spacing:.06em;text-transform:uppercase;color:#8a9499;margin-bottom:6px;">Maks. observert</div>
            <div style="font-family:'Newsreader',serif;font-size:27px;font-weight:500;color:#1c2a2e;line-height:1;">{_fmt(h.get("maks_m3s"),1)}<span style="font-size:14px;color:#6b7a7e;font-family:'IBM Plex Sans';margin-left:3px;">m³/s</span></div>
          </div>
        </div>
        <div style="display:grid;grid-template-columns:1fr 1fr;gap:14px;margin-top:18px;">
          <div style="background:#f4f2ec;padding:16px 20px;border-radius:2px;">
            <div style="font-size:10.5px;letter-spacing:.1em;text-transform:uppercase;color:#8a7e63;margin-bottom:6px;">Estimert slukeevne</div>
            <div style="font-family:'Newsreader',serif;font-size:24px;font-weight:500;color:#1c2a2e;">{_fmt(pr.get("slukeevne_ls",0)/1000,3)} m³/s</div>
            <div style="font-size:12px;color:#6b7a7e;margin-top:4px;">Basert på produksjonsestimat</div>
          </div>
          <div style="background:#f4f2ec;padding:16px 20px;border-radius:2px;">
            <div style="font-size:10.5px;letter-spacing:.1em;text-transform:uppercase;color:#8a7e63;margin-bottom:6px;">Estimert produksjon</div>
            <div style="font-family:'Newsreader',serif;font-size:24px;font-weight:500;color:#1c2a2e;">{_fmt(pr.get("produksjon_gwh",0),1)} GWh/år</div>
            <div style="font-size:12px;color:#6b7a7e;margin-top:4px;">Foreløpig estimat</div>
          </div>
        </div>"""
    else:
        feil = h.get("feil", "Ukjent feil")
        hydrologi_stasjon_html = f'<p style="color:#8a9499;font-size:13px;background:#f4f2ec;padding:14px 16px;border-radius:2px;">Hydrologidata ikke tilgjengelig: {feil}</p>'

    return f"""<!DOCTYPE html>
<html lang="no">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Fossekall Analyserapport — {p.get("navn","")}</title>
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link href="https://fonts.googleapis.com/css2?family=Newsreader:ital,opsz,wght@0,6..72,400;0,6..72,500;0,6..72,600;1,6..72,400&family=IBM+Plex+Sans:wght@400;500;600;700&display=swap" rel="stylesheet">
<style>
  body {{ margin:0; background:#fff; color:#283539; font-family:"IBM Plex Sans",system-ui,sans-serif; }}
  .doc {{ box-sizing:border-box; max-width:8.5in; margin:0 auto; background:inherit; padding:56px clamp(24px,5vw,.85in) 96px; }}
  .doc-frame {{ width:100%; border-collapse:collapse; }}
  .doc-frame td {{ padding:0; }}
  .running-hdr, .running-ftr, .hdr-space, .ftr-space {{ display:none; }}
  h1,h2,h3 {{ text-wrap:balance; }}
  p,li {{ text-wrap:pretty; }}
  @page {{ size:letter; margin:0; }}
  @media print {{
    html {{ -webkit-print-color-adjust:exact; print-color-adjust:exact; }}
    html,body {{ margin:0; padding:0; }}
    .doc {{ max-width:none!important; margin:0!important; padding:0 .75in!important; box-shadow:none!important; border:none!important; }}
    .hdr-space,.ftr-space {{ display:table-cell; height:.7in!important; }}
    .running-hdr,.running-ftr {{ display:flex!important; justify-content:space-between; align-items:baseline;
      position:fixed!important; left:0; right:0; margin:0!important;
      font-size:10px; letter-spacing:.08em; text-transform:uppercase; color:#8a9499; font-family:"IBM Plex Sans",sans-serif; }}
    .running-hdr {{ top:0; padding:.32in .75in 0!important; }}
    .running-ftr {{ bottom:0; padding:0 .75in .32in!important; }}
    h1,h2,h3,h4,h5,h6 {{ break-after:avoid; }}
    figure,pre,blockquote,img,svg,tr,.keep {{ break-inside:avoid; }}
    p,li {{ orphans:3; widows:3; }}
    .screen-only {{ display:none!important; }}
  }}
</style>
</head>
<body>
<main class="doc">
  <table class="doc-frame" role="presentation">
    <thead><tr><td class="hdr-space"></td></tr></thead>
    <tbody><tr><td>

      <div class="running-hdr"><span>Fossekall Analyserapport</span><span>{p.get("navn","")}</span></div>
      <div class="running-ftr"><span>{p.get("kommune","")}, {p.get("fylke","")}</span><span>Generert {p.get("dato","")}</span></div>

      <!-- TITTEL -->
      <div style="display:flex;align-items:flex-end;justify-content:space-between;gap:24px;border-bottom:2px solid #283539;padding-bottom:18px;">
        <div>
          <div style="font-size:11px;letter-spacing:.22em;text-transform:uppercase;color:#2f6b73;font-weight:600;margin-bottom:12px;">Analyserapport</div>
          <h1 style="font-family:'Newsreader',serif;font-weight:500;font-size:42px;line-height:1.04;margin:0;color:#1c2a2e;letter-spacing:-.01em;">Fossekall<br>Analyserapport</h1>
        </div>
        <div style="text-align:right;font-size:12.5px;line-height:1.7;color:#5b6a6e;padding-bottom:4px;">
          <div style="font-family:'Newsreader',serif;font-style:italic;font-size:17px;color:#2f6b73;">{p.get("navn","")}</div>
          <div>{p.get("kommune","")}{" · " + p.get("fylke","") if p.get("fylke") else ""}</div>
          <div>{p.get("dato","")}</div>
        </div>
      </div>

      <!-- 01. PROSJEKTINFO -->
      <section style="margin-top:40px;">
        <div class="keep" style="display:flex;align-items:baseline;gap:14px;margin-bottom:18px;">
          <span style="font-family:'Newsreader',serif;font-size:24px;color:#9aa6a3;font-weight:500;min-width:34px;">01</span>
          <h2 style="font-family:'Newsreader',serif;font-weight:600;font-size:24px;margin:0;color:#1c2a2e;">Prosjektinfo</h2>
        </div>
        <div style="display:grid;grid-template-columns:repeat(3,1fr);border-top:1px solid #dfdcd3;">
          <div style="padding:14px 16px 14px 0;border-bottom:1px solid #ece9e1;">
            <div style="font-size:10.5px;letter-spacing:.1em;text-transform:uppercase;color:#8a9499;margin-bottom:5px;">Prosjektnavn</div>
            <div style="font-size:15.5px;font-weight:500;color:#283539;">{p.get("navn","–")}</div>
          </div>
          <div style="padding:14px 16px;border-bottom:1px solid #ece9e1;">
            <div style="font-size:10.5px;letter-spacing:.1em;text-transform:uppercase;color:#8a9499;margin-bottom:5px;">Søker</div>
            <div style="font-size:15.5px;font-weight:500;color:#283539;">{p.get("soker","–")}</div>
          </div>
          <div style="padding:14px 0 14px 16px;border-bottom:1px solid #ece9e1;">
            <div style="font-size:10.5px;letter-spacing:.1em;text-transform:uppercase;color:#8a9499;margin-bottom:5px;">Dato</div>
            <div style="font-size:15.5px;font-weight:500;color:#283539;">{p.get("dato","–")}</div>
          </div>
          <div style="padding:14px 16px 14px 0;">
            <div style="font-size:10.5px;letter-spacing:.1em;text-transform:uppercase;color:#8a9499;margin-bottom:5px;">Kommune</div>
            <div style="font-size:15.5px;font-weight:500;color:#283539;">{p.get("kommune","–")}</div>
          </div>
          <div style="padding:14px 16px;">
            <div style="font-size:10.5px;letter-spacing:.1em;text-transform:uppercase;color:#8a9499;margin-bottom:5px;">Fylke</div>
            <div style="font-size:15.5px;font-weight:500;color:#283539;">{p.get("fylke","–")}</div>
          </div>
          <div style="padding:14px 0 14px 16px;">
            <div style="font-size:10.5px;letter-spacing:.1em;text-transform:uppercase;color:#8a9499;margin-bottom:5px;">Koordinater</div>
            <div style="font-size:15.5px;font-weight:500;color:#283539;">{p.get("lat","–")}°N, {p.get("lon","–")}°Ø</div>
          </div>
        </div>
      </section>

      <!-- 02. HYDROLOGI -->
      <section style="margin-top:44px;">
        <div class="keep" style="display:flex;align-items:baseline;gap:14px;margin-bottom:6px;">
          <span style="font-family:'Newsreader',serif;font-size:24px;color:#9aa6a3;font-weight:500;min-width:34px;">02</span>
          <h2 style="font-family:'Newsreader',serif;font-weight:600;font-size:24px;margin:0;color:#1c2a2e;">Hydrologi</h2>
        </div>
        <p style="margin:0 0 18px 48px;font-size:13px;color:#6b7a7e;line-height:1.6;">Vannføringsdata fra nærmeste NVE-målestasjon med daglige observasjoner.</p>
        {hydrologi_stasjon_html}
      </section>

      <!-- 03. BIOLOGI -->
      <section style="margin-top:44px;">
        <div class="keep" style="display:flex;align-items:baseline;gap:14px;margin-bottom:6px;">
          <span style="font-family:'Newsreader',serif;font-size:24px;color:#9aa6a3;font-weight:500;min-width:34px;">03</span>
          <h2 style="font-family:'Newsreader',serif;font-weight:600;font-size:24px;margin:0;color:#1c2a2e;">Biologi</h2>
        </div>
        <p style="margin:0 0 18px 48px;font-size:13px;color:#6b7a7e;line-height:1.6;">Funn fra Artskart og Naturbase innenfor {b.get("radius_km",10)} km radius.</p>

        <h3 style="font-family:'IBM Plex Sans';font-size:12px;letter-spacing:.1em;text-transform:uppercase;color:#5b6a6e;font-weight:600;margin:0 0 8px;">Rødlistede arter</h3>
        <table class="keep" style="width:100%;border-collapse:collapse;font-size:14px;margin-bottom:24px;">
          <thead>
            <tr style="border-bottom:1.5px solid #283539;">
              <th style="text-align:left;padding:8px 8px 8px 0;font-size:11px;letter-spacing:.05em;text-transform:uppercase;color:#8a9499;font-weight:600;">Art</th>
              <th style="text-align:left;padding:8px;font-size:11px;letter-spacing:.05em;text-transform:uppercase;color:#8a9499;font-weight:600;font-style:italic;">Vitenskapelig navn</th>
              <th style="text-align:center;padding:8px;font-size:11px;letter-spacing:.05em;text-transform:uppercase;color:#8a9499;font-weight:600;">Kategori</th>
              <th style="text-align:right;padding:8px 0 8px 8px;font-size:11px;letter-spacing:.05em;text-transform:uppercase;color:#8a9499;font-weight:600;">Obs.</th>
            </tr>
          </thead>
          <tbody>
            {_art_rader(b.get("arter", []))}
          </tbody>
        </table>

        <h3 style="font-family:'IBM Plex Sans';font-size:12px;letter-spacing:.1em;text-transform:uppercase;color:#5b6a6e;font-weight:600;margin:0 0 8px;">Naturtyper (Naturbase NiN)</h3>
        <div class="keep" style="display:grid;grid-template-columns:1fr 1fr;gap:12px;">
          {_naturtype_kort(b.get("naturtyper", []))}
        </div>
      </section>

      <!-- 04. PRODUKSJONSESTIMAT -->
      <section style="margin-top:44px;">
        <div class="keep" style="display:flex;align-items:baseline;gap:14px;margin-bottom:6px;">
          <span style="font-family:'Newsreader',serif;font-size:24px;color:#9aa6a3;font-weight:500;min-width:34px;">04</span>
          <h2 style="font-family:'Newsreader',serif;font-weight:600;font-size:24px;margin:0;color:#1c2a2e;">Produksjonsestimat</h2>
        </div>
        <p style="margin:0 0 18px 48px;font-size:13px;color:#6b7a7e;line-height:1.6;">Beregnet ut fra fallhøyde, nedbørfelt og regionale avrenningsdata.</p>

        <div style="display:grid;grid-template-columns:repeat(3,1fr);border-top:1px solid #dfdcd3;margin-bottom:18px;">
          <div style="padding:14px 16px 14px 0;border-bottom:1px solid #ece9e1;">
            <div style="font-size:10.5px;letter-spacing:.1em;text-transform:uppercase;color:#8a9499;margin-bottom:5px;">Fallhøyde</div>
            <div style="font-size:15.5px;font-weight:500;">{pr.get("fallhoyde_m","–")} m</div>
          </div>
          <div style="padding:14px 16px;border-bottom:1px solid #ece9e1;">
            <div style="font-size:10.5px;letter-spacing:.1em;text-transform:uppercase;color:#8a9499;margin-bottom:5px;">Nedbørfelt</div>
            <div style="font-size:15.5px;font-weight:500;">{_fmt(pr.get("nedborfelt_km2"),1)} km²</div>
          </div>
          <div style="padding:14px 0 14px 16px;border-bottom:1px solid #ece9e1;">
            <div style="font-size:10.5px;letter-spacing:.1em;text-transform:uppercase;color:#8a9499;margin-bottom:5px;">Region</div>
            <div style="font-size:15.5px;font-weight:500;">{pr.get("region","–")}</div>
          </div>
        </div>

        <div class="keep" style="display:grid;grid-template-columns:1fr 1fr 1fr;gap:14px;">
          <div style="background:#1c2a2e;color:#fff;padding:20px;border-radius:2px;">
            <div style="font-size:10.5px;letter-spacing:.12em;text-transform:uppercase;color:#8fb0b3;margin-bottom:8px;">Installert effekt</div>
            <div style="font-family:'Newsreader',serif;font-size:34px;font-weight:500;line-height:1;">{_fmt(pr.get("installert_effekt_mw"),2)}<span style="font-size:16px;color:#a9c4c6;margin-left:4px;font-family:'IBM Plex Sans';">MW</span></div>
          </div>
          <div style="background:#2f6b73;color:#fff;padding:20px;border-radius:2px;">
            <div style="font-size:10.5px;letter-spacing:.12em;text-transform:uppercase;color:#bfe0e2;margin-bottom:8px;">Årsproduksjon</div>
            <div style="font-family:'Newsreader',serif;font-size:34px;font-weight:500;line-height:1;">{_fmt(pr.get("produksjon_gwh"),1)}<span style="font-size:16px;color:#cdeaeb;margin-left:4px;font-family:'IBM Plex Sans';">GWh</span></div>
          </div>
          <div style="background:#f4f2ec;padding:20px;border-radius:2px;display:flex;flex-direction:column;justify-content:center;">
            <div style="font-size:10.5px;letter-spacing:.12em;text-transform:uppercase;color:#8a7e63;margin-bottom:8px;">Kategori</div>
            <div style="font-family:'Newsreader',serif;font-size:22px;font-weight:600;color:#1c2a2e;line-height:1.1;">{pr.get("kategori","–").split(" ")[0]}</div>
            <div style="font-size:12px;color:#6b7a7e;margin-top:4px;">{" ".join(pr.get("kategori","").split(" ")[1:])}</div>
          </div>
        </div>
        <p style="margin:14px 0 0;font-size:12px;color:#8a9499;line-height:1.55;">Estimat basert på {pr.get("avrenning_mm","–")} mm/år spesifikk avrenning ({pr.get("region","")}). Erstatter ikke detaljert hydrologirapport.</p>
      </section>

      <!-- KILDER -->
      <div class="keep" style="margin-top:40px;padding-top:16px;border-top:1px solid #dfdcd3;font-size:11.5px;color:#8a9499;line-height:1.7;">
        <strong style="color:#6b7a7e;font-weight:600;">Kilder:</strong> NVE HydAPI (hydrologi) · Artsdatabanken — Artskart (artsfunn) · Miljødirektoratet — Naturbase NiN (naturtyper). Estimater er foreløpige og erstatter ikke detaljert konsekvensutredning.
      </div>

    </td></tr></tbody>
    <tfoot><tr><td class="ftr-space"></td></tr></tfoot>
  </table>
</main>
</body>
</html>"""


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
            data = json.loads(self.rfile.read(length))
            html = bygg_html(data)

            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.send_header("Access-Control-Allow-Origin", "*")
            self.end_headers()
            self.wfile.write(html.encode("utf-8"))

        except Exception as e:
            self.send_response(500)
            self.send_header("Content-Type", "application/json")
            self.send_header("Access-Control-Allow-Origin", "*")
            self.end_headers()
            self.wfile.write(json.dumps({"error": str(e)}).encode())

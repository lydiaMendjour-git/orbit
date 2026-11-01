"""
Habillage visuel du tableau de bord : thème sombre violet, lueurs, animations,
cartes, graphiques et images animées (jauge, barres de ratio, répartition des feux).
"""
import base64
import math
import re
from urllib.parse import unquote

import pandas as pd
import plotly.graph_objects as go
import streamlit as st

import calculs as c

NOM_APP = "ORBIT"
SOUS_NOM = "Radar des risques clients"

FOND, PANNEAU, BORD, TEXTE, GRIS = "#0A0612", "rgba(26,14,48,0.72)", "#3B2366", "#F3EEFF", "#B4A6D6"
VIOLET, LAVANDE, MAGENTA, PROFOND = "#A855F7", "#C4B5FD", "#E879F9", "#7C3AED"

CSS = """
<style>
@import url('https://fonts.googleapis.com/css2?family=Sora:wght@400;500;600;700;800&display=swap');
@property --n { syntax: '<integer>'; initial-value: 0; inherits: false; }

/* ---------- Fond : aurores violettes qui dérivent ---------- */
.stApp { background: #0A0612; }
.stApp::before, .stApp::after { content: ""; position: fixed; inset: -20%; z-index: 0; pointer-events: none; }
.stApp::before {
  background:
    radial-gradient(40% 35% at 15% 10%, rgba(168,85,247,.38), transparent 70%),
    radial-gradient(35% 30% at 85% 20%, rgba(232,121,249,.22), transparent 70%),
    radial-gradient(45% 40% at 70% 95%, rgba(124,58,237,.30), transparent 70%);
  filter: blur(20px); animation: aurore 18s ease-in-out infinite alternate; }
.stApp::after {
  background-image: radial-gradient(rgba(243,238,255,.55) 1px, transparent 1.4px);
  background-size: 120px 120px; opacity: .10; animation: etoiles 60s linear infinite; }
@keyframes aurore { 0% { transform: translate(0,0) scale(1) rotate(0deg); }
                    50% { transform: translate(4%,3%) scale(1.08) rotate(6deg); }
                    100% { transform: translate(-3%,5%) scale(1.03) rotate(-5deg); } }
@keyframes etoiles { to { background-position: 120px 240px; } }
[data-testid="stMain"], [data-testid="stHeader"] { position: relative; z-index: 1; }
[data-testid="stHeader"] { background: transparent; }
[data-testid="stSidebar"], [data-testid="stSidebarCollapsedControl"], [data-testid="stExpandSidebarButton"] { display: none !important; }
.block-container { padding-top: 1.2rem; max-width: 1560px; }
p, label, .stMarkdown, li { color: #F3EEFF; }

/* ---------- En-tête façon plateforme ---------- */
.st-key-entete { background: linear-gradient(120deg, rgba(76,29,149,.55), rgba(30,14,58,.85) 45%, rgba(88,28,135,.55));
  border: 1px solid #5B3A99; border-radius: 26px; padding: 22px 30px !important; margin-bottom: 6px;
  box-shadow: 0 10px 50px rgba(124,58,237,.35), inset 0 1px 0 rgba(255,255,255,.10); backdrop-filter: blur(16px);
  position: relative; overflow: hidden; animation: monte .7s cubic-bezier(.16,1,.3,1) both; }
.st-key-entete::after { content: ""; position: absolute; left: 0; right: 0; bottom: 0; height: 3px;
  background: linear-gradient(90deg, transparent, #A855F7, #E879F9, #A855F7, transparent); background-size: 200% 100%;
  animation: balaye 3s linear infinite; box-shadow: 0 0 18px #E879F9; }
.marque { display: flex; align-items: center; gap: 20px; }
.marque svg { width: 78px; height: 78px; filter: drop-shadow(0 0 18px rgba(232,121,249,.9)); flex: none; }
.marque .nom { font-family: 'Sora', sans-serif; font-size: 3rem; font-weight: 800; letter-spacing: 8px; line-height: 1;
  background: linear-gradient(90deg,#FFFFFF,#F0ABFC,#C084FC,#FFFFFF); background-size: 300% 100%;
  -webkit-background-clip: text; background-clip: text; color: transparent; animation: degrade 6s linear infinite;
  filter: drop-shadow(0 0 20px rgba(232,121,249,.5)); }
.marque .slogan { font-family: 'Sora', sans-serif; font-size: 1.05rem; letter-spacing: 4px; color: #E9D5FF; text-transform: uppercase;
  margin-top: 8px; font-weight: 500; }
@keyframes degrade { to { background-position: 300% 0; } }
.puces { display: flex; justify-content: flex-end; gap: 12px; flex-wrap: wrap; padding-top: 14px; }
.puce { font-family: 'Sora', sans-serif; background: rgba(10,6,18,.55); border: 1px solid #6D4BB0; border-radius: 999px;
  padding: 10px 18px; color: #E9D5FF; font-size: 1rem; display: flex; align-items: center; gap: 10px; }
.puce b { color: #FFFFFF; font-size: 1.15rem; }
.puce .point { width: 10px; height: 10px; border-radius: 50%; background: #2EE59D; box-shadow: 0 0 10px #2EE59D;
  animation: respire 2s ease-in-out infinite; }

/* ---------- Navigation : grands onglets sur toute la largeur ---------- */
.st-key-nav { margin: 4px 0 4px 0; }
.st-key-nav [data-testid="stButtonGroup"], .st-key-nav [data-testid="stButtonGroup"] > div,
.st-key-nav [data-testid="stElementContainer"] { width: 100% !important; max-width: none !important; }
.st-key-nav [role="radiogroup"] { display: flex !important; width: 100% !important; gap: 12px; flex-wrap: wrap; }
.st-key-nav [role="radiogroup"] button * { max-width: none !important; overflow: visible !important; text-overflow: clip !important; white-space: nowrap !important; }
.st-key-nav [role="radiogroup"] button { flex: 1 1 auto !important; width: auto !important; max-width: none !important; padding: 0 18px !important; min-height: 66px; border-radius: 18px !important;
  background: rgba(30,16,56,.80) !important; border: 1.5px solid #4C2F85 !important; color: #D8C8F5 !important;
  font-family: 'Sora', sans-serif !important; transition: transform .25s, box-shadow .25s, border-color .25s, background .25s;
  box-shadow: 0 4px 18px rgba(0,0,0,.35); }
.st-key-nav [role="radiogroup"] button p { font-family: 'Sora', sans-serif !important; font-size: 1.12rem !important; font-weight: 600 !important; }
.st-key-nav [role="radiogroup"] button [data-testid="stIconEmoji"] { font-size: 1.5rem !important; }
.st-key-nav [role="radiogroup"] button:hover { transform: translateY(-3px); border-color: #C084FC !important; color: #FFFFFF !important;
  background: rgba(76,29,149,.55) !important; box-shadow: 0 0 26px rgba(192,132,252,.45); }
.st-key-nav [role="radiogroup"] button[aria-checked="true"] { color: #FFFFFF !important; border-color: #F0ABFC !important;
  background: linear-gradient(135deg,#6D28D9,#A855F7 55%,#E879F9) !important; background-size: 200% 200% !important;
  box-shadow: 0 0 30px rgba(168,85,247,.85), 0 0 60px rgba(232,121,249,.40), inset 0 1px 0 rgba(255,255,255,.35) !important;
  transform: translateY(-3px); animation: pilule 4s ease infinite; }
@keyframes pilule { 0%,100% { background-position: 0% 50%; } 50% { background-position: 100% 50%; } }

/* ---------- Barre de filtres ---------- */
.st-key-filtres { background: rgba(22,12,40,.70); border: 1px solid #3B2366; border-radius: 20px; padding: 14px 22px 18px 22px !important;
  margin-top: 8px; }
.st-key-filtres label p { font-family: 'Sora', sans-serif; font-size: .95rem !important; color: #E9D5FF !important; font-weight: 600; }

/* ---------- Titres ---------- */
.titre { font-family: 'Sora', sans-serif; margin: 1.2rem 0 .1rem 0; font-weight: 300; font-size: 2.8rem; color: #F3EEFF; letter-spacing: -.5px;
  animation: monte .7s cubic-bezier(.16,1,.3,1) both; }
.titre b { font-weight: 700; background: linear-gradient(90deg,#C084FC,#E879F9,#A855F7,#C084FC); background-size: 300% 100%;
  -webkit-background-clip: text; background-clip: text; color: transparent; animation: degrade 5s linear infinite;
  filter: drop-shadow(0 0 18px rgba(232,121,249,.45)); }
.sous-titre { color: #B4A6D6; font-size: 1.05rem; margin-bottom: .5rem; animation: monte .7s .1s cubic-bezier(.16,1,.3,1) both; }
.trait { height: 2px; border-radius: 2px; margin: .4rem 0 1.4rem 0;
  background: linear-gradient(90deg, transparent, #A855F7, #E879F9, #A855F7, transparent); background-size: 200% 100%;
  animation: balaye 3s linear infinite, deplie 1s cubic-bezier(.16,1,.3,1) both; transform-origin: left; box-shadow: 0 0 14px #A855F7; }
@keyframes balaye { to { background-position: -200% 0; } }
@keyframes deplie { from { transform: scaleX(0); } }
@keyframes monte { from { opacity: 0; transform: translateY(18px); } }
.panneau { font-family: 'Sora', sans-serif; font-size: 1.2rem; font-weight: 600; color: #F3EEFF; margin: .8rem 0 .6rem 0; display: flex; align-items: center; gap: 10px; }
.panneau::before { content: ""; width: 10px; height: 10px; border-radius: 50%; background: #E879F9;
  box-shadow: 0 0 12px #E879F9, 0 0 24px #A855F7; animation: respire 2.4s ease-in-out infinite; }
@keyframes respire { 50% { transform: scale(.6); opacity: .5; } }

/* ---------- Cartes chiffres ---------- */
.carte { position: relative; overflow: hidden; background: linear-gradient(160deg, rgba(40,20,72,.80), rgba(20,10,38,.80));
  border: 1px solid #3B2366; border-radius: 20px; padding: 18px 20px; min-height: 150px; margin-bottom: 14px;
  box-shadow: 0 0 28px rgba(168,85,247,.20), inset 0 1px 0 rgba(255,255,255,.06); backdrop-filter: blur(12px);
  animation: monte .8s cubic-bezier(.16,1,.3,1) both, halo 4s ease-in-out infinite; transition: transform .3s, box-shadow .3s; }
.carte:hover { transform: translateY(-6px) scale(1.02); box-shadow: 0 0 46px rgba(232,121,249,.45); border-color: #A855F7; }
.carte::after { content: ""; position: absolute; top: 0; left: -60%; width: 40%; height: 100%;
  background: linear-gradient(100deg, transparent, rgba(255,255,255,.10), transparent); transform: skewX(-20deg);
  animation: reflet 5s ease-in-out infinite; }
@keyframes reflet { 0%, 60% { left: -60%; } 100% { left: 140%; } }
@keyframes halo { 50% { box-shadow: 0 0 40px rgba(168,85,247,.38), inset 0 1px 0 rgba(255,255,255,.06); } }
.carte .lab { font-size: .78rem; letter-spacing: 1.6px; color: #C4B5FD; font-weight: 600; text-transform: uppercase; }
.carte .val { font-size: 2.7rem; font-weight: 300; color: #F3EEFF; margin-top: 6px; font-variant-numeric: tabular-nums; line-height: 1.1;
  text-shadow: 0 0 22px rgba(196,181,253,.45); }
.carte .sub { font-size: .9rem; color: #B4A6D6; margin-top: 4px; }
.compte { animation: compte 1.8s cubic-bezier(.16,1,.3,1) forwards; counter-reset: n var(--n); }
.compte::after { content: counter(n); }
@keyframes compte { from { --n: 0; } to { --n: var(--cible); } }
.orbe { position: absolute; top: 18px; right: 20px; width: 14px; height: 14px; border-radius: 50%; }
.orbe::before, .orbe::after { content: ""; position: absolute; inset: 0; border-radius: 50%; background: inherit; }
.orbe::before { filter: blur(8px); animation: respire 2s ease-in-out infinite; }
.orbe::after { animation: onde 1.8s ease-out infinite; opacity: .8; }
@keyframes onde { to { transform: scale(3.2); opacity: 0; } }
.carte.rouge { border-color: #6B2148; box-shadow: 0 0 34px rgba(255,77,109,.30); animation: monte .8s cubic-bezier(.16,1,.3,1) both, haloR 2.4s ease-in-out infinite; }
@keyframes haloR { 50% { box-shadow: 0 0 52px rgba(255,77,109,.50); } }
.carte.rouge .sub { color: #FF8FA3; }
[data-testid="stHorizontalBlock"] > div:nth-child(2) .carte { animation-delay: .08s, .5s; }
[data-testid="stHorizontalBlock"] > div:nth-child(3) .carte { animation-delay: .16s, 1s; }
[data-testid="stHorizontalBlock"] > div:nth-child(4) .carte { animation-delay: .24s, 1.5s; }
[data-testid="stHorizontalBlock"] > div:nth-child(5) .carte { animation-delay: .32s, 2s; }

/* ---------- Graphiques et tableaux ---------- */
[data-testid="stPlotlyChart"] { background: linear-gradient(160deg, rgba(36,18,66,.78), rgba(18,9,34,.78)); border: 1px solid #3B2366;
  border-radius: 20px; overflow: hidden; box-shadow: 0 0 30px rgba(168,85,247,.18); animation: monte .9s .2s cubic-bezier(.16,1,.3,1) both;
  transition: box-shadow .3s, border-color .3s; }
[data-testid="stPlotlyChart"]:hover { box-shadow: 0 0 46px rgba(232,121,249,.35); border-color: #A855F7; }
[data-testid="stPlotlyChart"] .cartesianlayer .plot, [data-testid="stPlotlyChart"] .pielayer { animation: revele 1.4s .35s cubic-bezier(.16,1,.3,1) both; }
@keyframes revele { from { clip-path: inset(0 100% 0 0); } to { clip-path: inset(0 0 0 0); } }
[data-testid="stPlotlyChart"] .trace.bars, [data-testid="stPlotlyChart"] .trace.scatter { filter: drop-shadow(0 0 6px rgba(232,121,249,.55)); }
[data-testid="stDataFrame"] { border: 1px solid #3B2366; border-radius: 16px; overflow: hidden; box-shadow: 0 0 26px rgba(168,85,247,.15);
  animation: monte .9s .3s cubic-bezier(.16,1,.3,1) both; }
.bloc-img { animation: monte .8s cubic-bezier(.16,1,.3,1) both; }
.infos { display: flex; gap: 34px; flex-wrap: wrap; margin-top: 8px; }
.infos div { color: #B4A6D6; font-size: .95rem; } .infos b { color: #F3EEFF; font-size: 1.3rem; font-weight: 600; margin-left: 8px; }
.raisons { background: linear-gradient(120deg, rgba(255,77,109,.10), rgba(168,85,247,.10)); border: 1px solid #5B2A6E; border-radius: 16px;
  padding: 14px 18px; color: #F3EEFF; font-size: 1rem; margin: 4px 0 18px 0; box-shadow: 0 0 26px rgba(232,121,249,.15);
  animation: monte .8s .2s cubic-bezier(.16,1,.3,1) both; }
.etat { text-align: center; font-weight: 600; font-size: 1.25rem; margin-top: -4px; text-shadow: 0 0 16px currentColor; }
.jauge-box { animation: monte .8s cubic-bezier(.16,1,.3,1) both; filter: drop-shadow(0 0 22px rgba(168,85,247,.45)); }
table.ratios { width: 100%; border-collapse: collapse; font-size: .95rem; }
table.ratios th { text-align: left; color: #C4B5FD; font-weight: 600; padding: 6px 8px; border-bottom: 1px solid #3B2366; }
table.ratios td { padding: 5px 8px; border-bottom: 1px solid #24163F; color: #F3EEFF; vertical-align: middle; }
table.ratios tr { animation: monte .6s cubic-bezier(.16,1,.3,1) both; transition: background .2s; }
table.ratios tr:hover td { background: rgba(168,85,247,.10); }
table.ratios td.num { text-align: right; font-variant-numeric: tabular-nums; white-space: nowrap; }
table.ratios td.mut { color: #B4A6D6; font-size: .82rem; white-space: nowrap; }

/* Champs de filtre */
[data-baseweb="select"] > div, [data-testid="stPopover"] button { background: rgba(26,14,48,.75) !important; border-color: #3B2366 !important;
  border-radius: 14px !important; transition: box-shadow .25s, border-color .25s; }
[data-baseweb="select"] > div:hover, [data-testid="stPopover"] button:hover { border-color: #A855F7 !important; box-shadow: 0 0 18px rgba(168,85,247,.35); }
[data-baseweb="tag"] { background: linear-gradient(135deg,#7C3AED,#A855F7) !important; }
</style>
"""

LOGO_SVG = """<svg viewBox='0 0 60 60' xmlns='http://www.w3.org/2000/svg'>
<defs><linearGradient id='lg' x1='0' y1='0' x2='1' y2='1'><stop offset='0' stop-color='#E879F9'/><stop offset='1' stop-color='#7C3AED'/></linearGradient></defs>
<circle cx='30' cy='30' r='9' fill='url(#lg)'><animate attributeName='r' values='8;10;8' dur='2.4s' repeatCount='indefinite'/></circle>
<ellipse cx='30' cy='30' rx='26' ry='10' fill='none' stroke='#C4B5FD' stroke-opacity='.55' stroke-width='1.4' transform='rotate(-25 30 30)'/>
<ellipse cx='30' cy='30' rx='26' ry='10' fill='none' stroke='#E879F9' stroke-opacity='.35' stroke-width='1.2' transform='rotate(35 30 30)'/>
<g><animateTransform attributeName='transform' type='rotate' from='0 30 30' to='360 30 30' dur='5s' repeatCount='indefinite'/>
<circle cx='56' cy='30' r='3' fill='#F3EEFF'/></g>
<g><animateTransform attributeName='transform' type='rotate' from='360 30 30' to='0 30 30' dur='8s' repeatCount='indefinite'/>
<circle cx='30' cy='6' r='2.4' fill='#E879F9'/></g></svg>"""


def entete(date_ref, n_clients: int):
    with st.container(key="entete"):
        g, d = st.columns([3, 2], vertical_alignment="center")
        g.markdown(f"<div class='marque'>{LOGO_SVG}<div><div class='nom'>{NOM_APP}</div><div class='slogan'>{SOUS_NOM}</div></div></div>",
                   unsafe_allow_html=True)
        d.markdown(f"<div class='puces'><div class='puce'><span class='point'></span>Données au <b>{date_ref:%d/%m/%Y}</b></div>"
                   f"<div class='puce'>👥 <b>{n_clients}</b> clients</div></div>", unsafe_allow_html=True)


def titre(t: str, sous: str):
    mots = t.split(" ", 1)
    html = f"<b>{mots[0]}</b>" + (f" {mots[1]}" if len(mots) > 1 else "")
    st.markdown(f"<div class='titre'>{html}</div><div class='sous-titre'>{sous}</div><div class='trait'></div>", unsafe_allow_html=True)


def panneau(t: str):
    st.markdown(f"<div class='panneau'>{t}</div>", unsafe_allow_html=True)


TONS = {"rouge": "#FF4D6D", "orange": "#FFB547", "vert": "#2EE59D", "violet": "#E879F9"}


def carte(lab: str, val, sub: str = "", ton: str | None = None) -> str:
    """Carte chiffre. Les nombres entiers défilent de 0 à leur valeur ; ton ajoute une pastille lumineuse."""
    txt = str(val)
    if re.fullmatch(r"\d[\d  ]*", txt):
        n = int(re.sub(r"\D", "", txt))
        txt = f"<span class='compte' style='--cible:{n}'></span>"
    orbe = f"<span class='orbe' style='background:{TONS[ton]}'></span>" if ton else ""
    cls = "carte rouge" if ton == "rouge" else "carte"
    return f"<div class='{cls}'>{orbe}<div class='lab'>{lab}</div><div class='val'>{txt}</div><div class='sub'>{sub}</div></div>"


def carte_alerte(n: int, part: float) -> str:
    return carte("Clients en rouge", int(n), f"{part * 100:.1f} % du portefeuille".replace(".", ","), "rouge")


def ligne_infos(paires) -> str:
    return "<div class='infos'>" + "".join(f"<div>{a}<b>{b}</b></div>" for a, b in paires) + "</div>"


def evol(e) -> str:
    if e is None or pd.isna(e):
        return "pas d'exercice précédent"
    col = "#2EE59D" if e >= 0 else "#FF4D6D"
    fl = "▲" if e >= 0 else "▼"
    return f"<span style='color:{col}'>{fl} {e * 100:+.1f} %</span> vs N-1".replace(".", ",")


def img(data_uri: str, largeur: str) -> str:
    """Les images SVG sont passées en base64 pour être affichées telles quelles (animations comprises)."""
    svg = unquote(data_uri.split(",", 1)[1])
    b64 = base64.b64encode(svg.encode("utf-8")).decode()
    return f"<img class='bloc-img' src='data:image/svg+xml;base64,{b64}' style='width:{largeur};max-width:100%;display:block'>"


def graphe(fig: go.Figure, t: str, h: int, legende: bool = False):
    fig.update_layout(template="plotly_dark", height=h, paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
                      title={"text": t, "font": {"size": 16, "color": TEXTE}, "x": 0.03, "y": 0.95},
                      font={"color": GRIS, "size": 13, "family": "Plus Jakarta Sans, Segoe UI, sans-serif"},
                      margin={"l": 14, "r": 14, "t": 54, "b": 14},
                      showlegend=legende, legend={"orientation": "h", "y": 1.1, "x": 1, "xanchor": "right"},
                      bargap=0.28, barmode="group",
                      hoverlabel={"bgcolor": "#1E1238", "bordercolor": VIOLET, "font": {"color": TEXTE, "size": 13}})
    fig.update_xaxes(showgrid=False, linecolor=BORD)
    fig.update_yaxes(gridcolor="#2A1A47", griddash="dot", zeroline=False)
    fig.update_traces(selector={"type": "bar"}, marker_line_width=0, marker_cornerradius=6)
    st.plotly_chart(fig, width="stretch", config={"displayModeBar": False})


def table_ratios(det: pd.DataFrame) -> str:
    lignes = []
    for i, (_, r) in enumerate(det.iterrows()):
        stt = r["statut"]
        code = -1 if pd.isna(stt) else int(stt)
        barre_img = ""
        if pd.notna(r["valeur"]):
            barre_img = img(barre(r["valeur"], code, r["sens"], r["orange"], r["rouge"]), "180px")
        lignes.append(
            f"<tr style='animation-delay:{i * 0.06:.2f}s'><td>{c.EMOJI[code]} {r['indicateur']}</td>"
            f"<td class='num'>{c.format_valeur(r['valeur'], r['unite'])}</td>"
            f"<td class='num' style='color:#B4A6D6'>{c.format_valeur(r['valeur_n1'], r['unite'])}</td>"
            f"<td>{barre_img}</td>"
            f"<td class='mut'>{c.seuil_texte(r['sens'], r['orange'], r['rouge'], r['unite'])}</td></tr>")
    return ("<table class='ratios'><tr><th>Ratio</th><th style='text-align:right'>N</th><th style='text-align:right'>N-1</th>"
            "<th>Position</th><th>Seuils</th></tr>" + "".join(lignes) + "</table>")


# ---------------------------------------------------------------------------
# Images SVG animées (mêmes dessins que les mesures Power BI)
# ---------------------------------------------------------------------------
def f1(x): return f"{x:.1f}"
def fr(x): return f"{x:.1f}".replace(".", ",")
HEAD = "data:image/svg+xml;utf8,"
COL = {2: "%23FF4D6D", 1: "%23FFB547", 0: "%232EE59D", -1: "%236B5A8E"}

def jauge(s):
    v = 0 if s is None else min(max(s, 0), 100)
    coul = "%236B5A8E" if s is None else "%23FF4D6D" if s >= 50 else "%23FFB547" if s >= 25 else "%232EE59D"
    c = 2 * math.pi * 52; circ = f1(c); fin = f1(c * (1 - v / 100)); txt = "-" if s is None else str(round(s))
    anim = f"<animate attributeName='stroke-dashoffset' from='{circ}' to='{fin}' dur='1.4s' fill='freeze' calcMode='spline' keyTimes='0;1' keySplines='0.16 1 0.3 1'/>"
    arc = f"<circle cx='70' cy='70' r='52' fill='none' stroke='{coul}' stroke-width='10' stroke-linecap='round' stroke-dasharray='{circ}' stroke-dashoffset='{fin}' transform='rotate(-90 70 70)'"
    return (HEAD + "<svg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 140 140' width='140' height='140'>"
            "<defs><filter id='g' x='-50%25' y='-50%25' width='200%25' height='200%25'><feGaussianBlur stdDeviation='4'/></filter></defs>"
            "<circle cx='70' cy='70' r='52' fill='none' stroke='%232A1A47' stroke-width='10'/>"
            + arc + " filter='url(%23g)' opacity='0.7'>" + anim + "</circle>" + arc + ">" + anim + "</circle>"
            f"<text x='70' y='78' text-anchor='middle' font-family='Segoe UI Light, Segoe UI' font-size='36' fill='%23F3EEFF'>{txt}"
            "<animate attributeName='opacity' from='0' to='1' dur='0.9s' fill='freeze'/></text>"
            "<text x='70' y='99' text-anchor='middle' font-family='Segoe UI' font-size='9' letter-spacing='1.5' fill='%23B4A6D6'>RISQUE / 100</text></svg>")

def pastille(code):
    coul = COL[code]
    onde = {2: f"<circle cx='12' cy='12' r='5' fill='none' stroke='{coul}' stroke-width='2'><animate attributeName='r' values='5;11' dur='1.4s' repeatCount='indefinite'/><animate attributeName='opacity' values='0.9;0' dur='1.4s' repeatCount='indefinite'/></circle>",
            1: f"<circle cx='12' cy='12' r='5' fill='none' stroke='{coul}' stroke-width='1.5'><animate attributeName='r' values='5;9' dur='2.4s' repeatCount='indefinite'/><animate attributeName='opacity' values='0.6;0' dur='2.4s' repeatCount='indefinite'/></circle>"}.get(code, "")
    coeur = (f"<circle cx='12' cy='12' r='4' fill='none' stroke='{coul}' stroke-width='1.5'/>" if code == -1 else
             f"<circle cx='12' cy='12' r='5.5' fill='{coul}' filter='url(%23g)' opacity='0.8'/><circle cx='12' cy='12' r='4' fill='{coul}'/>")
    return (HEAD + "<svg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 24 24' width='24' height='24'>"
            "<defs><filter id='g' x='-50%25' y='-50%25' width='200%25' height='200%25'><feGaussianBlur stdDeviation='1.6'/></filter></defs>" + onde + coeur + "</svg>")

def barre(v, st, sens, o, r):
    m = max(o, r) * 2; W = 220; xo = W * o / m; xr = W * r / m; xv = W * min(max(v, 0), m) / m; coul = COL[st]
    a = xo if sens == "haut" else xr; b = xr if sens == "haut" else xo
    c1 = "%232EE59D" if sens == "haut" else "%23FF4D6D"; c3 = "%23FF4D6D" if sens == "haut" else "%232EE59D"
    zones = (f"<rect x='0' y='12' width='{f1(a)}' height='5' rx='2.5' fill='{c1}' opacity='0.22'/>"
             f"<rect x='{f1(a)}' y='12' width='{f1(b - a)}' height='5' fill='%23FFB547' opacity='0.22'/>"
             f"<rect x='{f1(b)}' y='12' width='{f1(W - b)}' height='5' rx='2.5' fill='{c3}' opacity='0.22'/>")
    fx = f1(xv); gl = "dur='1.1s' fill='freeze' calcMode='spline' keyTimes='0;1' keySplines='0.16 1 0.3 1'"
    return (HEAD + "<svg xmlns='http://www.w3.org/2000/svg' viewBox='-6 0 232 28' width='232' height='28'>"
            "<defs><filter id='g' x='-100%25' y='-100%25' width='300%25' height='300%25'><feGaussianBlur stdDeviation='2.5'/></filter></defs>" + zones +
            f"<rect x='0' y='12' width='{fx}' height='5' rx='2.5' fill='{coul}'><animate attributeName='width' from='0' to='{fx}' {gl}/></rect>"
            f"<circle cx='{fx}' cy='14.5' r='7' fill='{coul}' filter='url(%23g)' opacity='0.8'><animate attributeName='cx' from='0' to='{fx}' {gl}/></circle>"
            f"<circle cx='{fx}' cy='14.5' r='4.5' fill='%23F3EEFF' stroke='{coul}' stroke-width='2'><animate attributeName='cx' from='0' to='{fx}' {gl}/></circle></svg>")

def courbe(vals):  # vals[i] = solde il y a i mois (i=0 aujourd'hui)
    W, H, p = 300, 80, 8; mn, mx = min(vals), max(vals); ec = 1 if mx == mn else mx - mn
    pts = [((11 - i) * W / 11, p + (mx - v) / ec * (H - 2 * p)) for i, v in enumerate(vals)]
    ch = "M" + " L".join(f"{f1(x)} {f1(y)}" for x, y in reversed(pts))
    coul = "%23C084FC" if vals[0] >= vals[11] else "%23FF4D6D"; y0 = p + mx / ec * (H - 2 * p)
    lz = f"<line x1='0' x2='{W}' y1='{f1(y0)}' y2='{f1(y0)}' stroke='%23FF4D6D' stroke-width='1' stroke-dasharray='3 4' opacity='0.6'/>" if mn < 0 < mx else ""
    return (HEAD + f"<svg xmlns='http://www.w3.org/2000/svg' viewBox='-4 0 312 {H}' width='312' height='{H}'><defs>"
            f"<linearGradient id='a' x1='0' x2='0' y1='0' y2='1'><stop offset='0' stop-color='{coul}' stop-opacity='0.35'/><stop offset='1' stop-color='{coul}' stop-opacity='0'/></linearGradient>"
            "<filter id='g' x='-20%25' y='-50%25' width='140%25' height='200%25'><feGaussianBlur stdDeviation='3'/></filter></defs>" + lz +
            f"<path d='{ch} L{W} {H} L0 {H} Z' fill='url(%23a)' opacity='1'><animate attributeName='opacity' from='0' to='1' dur='1.6s' fill='freeze'/></path>"
            f"<path d='{ch}' fill='none' stroke='{coul}' stroke-width='4' filter='url(%23g)' opacity='0.6' pathLength='1' stroke-dasharray='1' stroke-dashoffset='0'><animate attributeName='stroke-dashoffset' from='1' to='0' dur='1.6s' fill='freeze'/></path>"
            f"<path d='{ch}' fill='none' stroke='{coul}' stroke-width='2' stroke-linejoin='round' pathLength='1' stroke-dasharray='1' stroke-dashoffset='0'><animate attributeName='stroke-dashoffset' from='1' to='0' dur='1.6s' fill='freeze'/></path>"
            f"<circle cx='{W}' cy='{f1(pts[0][1])}' r='4' fill='{coul}'><animate attributeName='r' values='4;7;4' dur='1.8s' begin='1.6s' repeatCount='indefinite'/></circle></svg>")

def repartition(nR, nO, nV, n):
    nN = max(n - nR - nO - nV, 0); W = 600; wR, wO, wV, wN = [W * x / n for x in (nR, nO, nV, nN)]
    b = (f"<rect x='0' y='8' width='{f1(wR)}' height='14' fill='%23FF4D6D'/>"
         f"<rect x='{f1(wR)}' y='8' width='{f1(wO)}' height='14' fill='%23FFB547'/>"
         f"<rect x='{f1(wR + wO)}' y='8' width='{f1(wV)}' height='14' fill='%232EE59D'/>"
         f"<rect x='{f1(wR + wO + wV)}' y='8' width='{f1(wN)}' height='14' fill='%236B5A8E'/>")
    leg = ("<g font-family='Segoe UI' font-size='12' fill='%23B4A6D6'>"
           f"<circle cx='6' cy='50' r='4' fill='%23FF4D6D'/><text x='16' y='54'>Rouge <tspan fill='%23F3EEFF' font-weight='600'>{nR}</tspan></text>"
           f"<circle cx='156' cy='50' r='4' fill='%23FFB547'/><text x='166' y='54'>Orange <tspan fill='%23F3EEFF' font-weight='600'>{nO}</tspan></text>"
           f"<circle cx='306' cy='50' r='4' fill='%232EE59D'/><text x='316' y='54'>Vert <tspan fill='%23F3EEFF' font-weight='600'>{nV}</tspan></text>"
           f"<circle cx='456' cy='50' r='4' fill='%236B5A8E'/><text x='466' y='54'>Non évalué <tspan fill='%23F3EEFF' font-weight='600'>{nN}</tspan></text></g>")
    return (HEAD + "<svg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 600 64' width='600' height='64'><defs>"
            "<clipPath id='c'><rect x='0' y='0' width='600' height='30' rx='7'><animate attributeName='width' from='0' to='600' dur='1.3s' fill='freeze' calcMode='spline' keyTimes='0;1' keySplines='0.16 1 0.3 1'/></rect></clipPath>"
            "<filter id='g' x='-10%25' y='-100%25' width='120%25' height='300%25'><feGaussianBlur stdDeviation='6'/></filter></defs>"
            "<g clip-path='url(%23c)'><g filter='url(%23g)' opacity='0.55'>" + b + "</g>" + b + "</g>" + leg + "</svg>")

def badge(e):
    up = e >= 0; coul = "%232EE59D" if up else "%23FF4D6D"; txt = ("+" if up else "") + fr(e * 100) + " %25"
    fl = "M10 17 L15 10 L20 17" if up else "M10 11 L15 18 L20 11"
    return (HEAD + "<svg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 96 28' width='96' height='28'>"
            f"<rect x='1' y='1' width='94' height='26' rx='13' fill='{coul}' fill-opacity='0.14' stroke='{coul}' stroke-opacity='0.55'/>"
            f"<path d='{fl}' fill='none' stroke='{coul}' stroke-width='2.4' stroke-linecap='round' stroke-linejoin='round'><animateTransform attributeName='transform' type='translate' values='0 {3 if up else -3};0 0' dur='0.8s' fill='freeze'/></path>"
            f"<text x='58' y='18.5' text-anchor='middle' font-family='Segoe UI Semibold, Segoe UI' font-size='12' fill='{coul}'>{txt}</text></svg>")

def svg_carte(nR, part):
    return (HEAD + "<svg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 250 110' width='250' height='110'>"
            "<defs><filter id='g' x='-100%25' y='-100%25' width='300%25' height='300%25'><feGaussianBlur stdDeviation='8'/></filter></defs>"
            "<circle cx='212' cy='38' r='16' fill='%23FF4D6D' filter='url(%23g)' opacity='0.5'><animate attributeName='opacity' values='0.25;0.75;0.25' dur='2.2s' repeatCount='indefinite'/><animate attributeName='r' values='14;20;14' dur='2.2s' repeatCount='indefinite'/></circle>"
            "<circle cx='212' cy='38' r='7' fill='%23FF4D6D'/>"
            "<text x='4' y='22' font-family='Segoe UI Semibold, Segoe UI' font-size='11' letter-spacing='1.2' fill='%23B4A6D6'>CLIENTS EN ROUGE</text>"
            f"<text x='2' y='74' font-family='Segoe UI Light, Segoe UI' font-size='46' fill='%23F3EEFF'>{nR}<animate attributeName='y' values='90;74' dur='0.7s' fill='freeze' calcMode='spline' keyTimes='0;1' keySplines='0.16 1 0.3 1'/><animate attributeName='opacity' values='0;1' dur='0.7s' fill='freeze'/></text>"
            f"<text x='4' y='98' font-family='Segoe UI' font-size='11' fill='%23FF4D6D'>{fr(part * 100)} %25 du portefeuille</text></svg>")

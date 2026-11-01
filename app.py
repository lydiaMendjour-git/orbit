"""
ORBIT, radar des risques clients : prototype Python.

Lancement :  streamlit run app.py
Le navigateur s'ouvre tout seul sur http://localhost:8501
"""
from pathlib import Path

import pandas as pd
import plotly.graph_objects as go
import streamlit as st

import calculs as c
import visuels as vz

DOSSIER = Path(__file__).parent
FICHIER_PAR_DEFAUT = DOSSIER / "donnees" / "donnees_fictives_data_sharing.xlsx"

st.set_page_config(page_title="ORBIT · Radar des risques", page_icon="🪐", layout="wide", initial_sidebar_state="collapsed")
st.markdown(vz.CSS, unsafe_allow_html=True)


# ---------------------------------------------------------------------------
# Données (mises en cache : le calcul ne se refait que si le fichier change)
# ---------------------------------------------------------------------------
@st.cache_data(show_spinner="Lecture du fichier Excel…")
def lire(source_bytes: bytes | None, chemin: str):
    import io
    return c.charger(io.BytesIO(source_bytes) if source_bytes else chemin)


@st.cache_data(show_spinner="Calcul des ratios et des feux…")
def calculer(source_bytes: bytes | None, chemin: str, rang: int):
    return c.calculer(lire(source_bytes, chemin), rang)


# ---------------------------------------------------------------------------
# En-tête, navigation et filtres (en haut de page, plus de barre latérale)
# ---------------------------------------------------------------------------
PAGES = ["Portefeuille", "Fiche client", "Comparaison sectorielle", "Trésorerie et BFR", "Conformité et qualité"]
ICONES = {"Portefeuille": "🪐", "Fiche client": "👤", "Comparaison sectorielle": "📊", "Trésorerie et BFR": "💧", "Conformité et qualité": "🛡️"}
if "rang" not in st.session_state:
    st.session_state.rang = 1
if "fichier" not in st.session_state:
    st.session_state.fichier = None

source = st.session_state.fichier
if not source and not FICHIER_PAR_DEFAUT.exists():
    st.error(f"Fichier introuvable : {FICHIER_PAR_DEFAUT}. Placez l'Excel dans le dossier « donnees ».")
    st.stop()
try:
    R = calculer(source, str(FICHIER_PAR_DEFAUT), st.session_state.rang)
except ValueError as e:
    st.error(str(e))
    st.stop()

vz.entete(R.date_ref, len(R.clients))
with st.container(key="nav"):
    page = st.segmented_control("Page", PAGES, default="Portefeuille", key="page", label_visibility="collapsed",
                                format_func=lambda p: f"{ICONES[p]}  {p}") or "Portefeuille"

barre_filtres = st.container(key="filtres")
f1, f2, f3, f4 = barre_filtres.columns([1.1, 1.4, 1.4, 0.7], vertical_alignment="bottom")
exo = f1.selectbox("Exercice analysé", ["Dernier exercice clôturé", "Exercice précédent"],
                   index=st.session_state.rang - 1)
if (1 if exo.startswith("Dernier") else 2) != st.session_state.rang:
    st.session_state.rang = 1 if exo.startswith("Dernier") else 2
    st.rerun()
sel_collab = f2.multiselect("Collaborateur", sorted(R.clients["collaborateur"].dropna().unique()), placeholder="Tous")
sel_cat = f3.multiselect("Catégorie", sorted(R.clients["secteur"].dropna().unique()), placeholder="Toutes")
with f4.popover("📂 Fichier", width="stretch"):
    envoi = st.file_uploader("Autre fichier Excel (même format)", type=["xlsx"])
    nouveau = envoi.getvalue() if envoi else None
    if nouveau != st.session_state.fichier:
        st.session_state.fichier = nouveau
        st.rerun()

def filtrer(df: pd.DataFrame) -> pd.DataFrame:
    if sel_collab:
        df = df[df["collaborateur"].isin(sel_collab)]
    if sel_cat:
        df = df[df["secteur"].isin(sel_cat)]
    return df

CL = filtrer(R.clients)
IDS = set(CL["company_id"])
if CL.empty:
    st.warning("Aucun client ne correspond aux filtres.")
    st.stop()


# ---------------------------------------------------------------------------
# Pages
# ---------------------------------------------------------------------------
def page_portefeuille():
    vz.titre("Risque du portefeuille", "Vue d'ensemble de tous les clients suivis")
    nR, nO, nV = (CL["feu_code"] == 2).sum(), (CL["feu_code"] == 1).sum(), (CL["feu_code"] == 0).sum()
    n = len(CL)
    k = st.columns(5)
    k[0].markdown(vz.carte_alerte(nR, nR / n), unsafe_allow_html=True)
    k[1].markdown(vz.carte("Clients suivis", n, f"{CL['score'].mean():.0f} de score de risque moyen", "violet"), unsafe_allow_html=True)
    k[2].markdown(vz.carte("Clients en orange", nO, "à surveiller", "orange"), unsafe_allow_html=True)
    tendue = int((CL["st_TRESO_JOURS"] == 2).sum())
    k[3].markdown(vz.carte("Trésorerie tendue", str(tendue), "moins de 15 jours de dépenses"), unsafe_allow_html=True)
    k[4].markdown(vz.carte("TVA en retard", str(int((CL["nb_tva_retard"] > 0).sum())), "clients concernés"), unsafe_allow_html=True)

    g, d1, d2 = st.columns([2, 1, 1])
    with g:
        vz.panneau("Répartition des feux du portefeuille")
        st.markdown(vz.img(vz.repartition(int(nR), int(nO), int(nV), n), "100%"), unsafe_allow_html=True)
        st.markdown(vz.ligne_infos([("Part en rouge", f"{nR / n * 100:.1f} %".replace(".", ",")),
                                    ("Dossiers peu fiables", str(int((CL["fiabilite"] == "Faible").sum()))),
                                    ("CA cumulé", c.euros(CL["ca"].sum()))]), unsafe_allow_html=True)
    with d1:
        cnt = CL["feu_code"].value_counts().reindex([2, 1, 0, -1], fill_value=0)
        fig = go.Figure(go.Bar(x=[c.FEUX[i] for i in cnt.index], y=cnt.values, marker_color=[c.COULEURS[i] for i in cnt.index],
                               text=cnt.values, textposition="outside"))
        vz.graphe(fig, "Clients par feu", 260)
    with d2:
        rc = CL[CL["feu_code"] == 2].groupby("collaborateur").size().sort_values()
        fig = go.Figure(go.Bar(x=rc.values, y=rc.index, orientation="h", marker_color=c.COULEURS[2]))
        vz.graphe(fig, "Clients en rouge par collaborateur", 260)

    vz.panneau("Clients à surveiller")
    t = CL.sort_values(["feu_code", "score"], ascending=False)[
        ["pastille", "client", "score", "secteur", "collaborateur", "MARGE_EBE", "TRESO_JOURS", "evolution_ca", "courbe_tresorerie", "raisons"]].copy()
    t["TRESO_JOURS"] = t["TRESO_JOURS"].round(0) + 0.0
    t["MARGE_EBE"] *= 100
    t["evolution_ca"] *= 100
    st.dataframe(t, hide_index=True, width="stretch", height=430, column_config={
        "pastille": st.column_config.TextColumn("Feu", width="small"),
        "client": "Client",
        "score": st.column_config.ProgressColumn("Score", min_value=0, max_value=100, format="%d"),
        "secteur": "Catégorie", "collaborateur": "Collaborateur",
        "MARGE_EBE": st.column_config.NumberColumn("Marge d'EBE", format="%.1f %%"),
        "TRESO_JOURS": st.column_config.NumberColumn("Tréso (jours)", format="%d"),
        "evolution_ca": st.column_config.NumberColumn("CA vs N-1", format="%+.1f %%"),
        "courbe_tresorerie": st.column_config.LineChartColumn("Trésorerie 12 mois", width="medium"),
        "raisons": st.column_config.TextColumn("Pourquoi ce feu", width="large"),
    })


def page_fiche():
    ordre = CL.sort_values(["feu_code", "score"], ascending=False)
    choix = st.selectbox("Client", ordre["client"].tolist(), format_func=lambda x: f"{ordre.set_index('client').at[x, 'pastille']}  {x}")
    x = CL[CL["client"] == choix].iloc[0]
    vz.titre(choix, f"{x['secteur']} · {x['forme_juridique']} · suivi par {x['collaborateur']}")
    if pd.isna(x["ca"]):
        st.info("Ce client n'a pas encore d'exercice clôturé pour la période choisie.")

    a, b = st.columns([1, 3])
    with a:
        st.markdown("<div class='jauge-box'>" + vz.img(vz.jauge(None if pd.isna(x["score"]) else x["score"]), "230px") + "</div>", unsafe_allow_html=True)
        st.markdown(f"<div class='etat' style='color:{c.COULEURS[int(x['feu_code'])]}'>{x['pastille']} {x['feu']}</div>", unsafe_allow_html=True)
    with b:
        k = st.columns(3)
        k[0].markdown(vz.carte("Chiffre d'affaires", c.euros(x["ca"]), vz.evol(x["evolution_ca"])), unsafe_allow_html=True)
        k[1].markdown(vz.carte("EBE", c.euros(x["ebe"]), f"N-1 : {c.euros(x['ebe_n1'])}"), unsafe_allow_html=True)
        k[2].markdown(vz.carte("Résultat net", c.euros(x["resultat_net"]), f"N-1 : {c.euros(x['rn_n1'])}"), unsafe_allow_html=True)
        k = st.columns(3)
        k[0].markdown(vz.carte("Solde bancaire", c.euros(x["solde_bancaire"]), "aujourd'hui"), unsafe_allow_html=True)
        k[1].markdown(vz.carte("Trésorerie en jours", c.format_valeur(x["TRESO_JOURS"], "jours"), "de dépenses couvertes"), unsafe_allow_html=True)
        k[2].markdown(vz.carte("Capitaux propres", c.euros(x["capitaux_propres"]), f"fiabilité des données : {x['fiabilite']}"), unsafe_allow_html=True)
    st.markdown(f"<div class='raisons'><b>Pourquoi ce feu</b><br>{x['raisons']}</div>", unsafe_allow_html=True)

    g, d = st.columns([1, 1])
    with g:
        etapes = [("Chiffre d'affaires", x["ca"]), ("Achats consommés", -x["achats_consommes"]), ("Charges externes", -x["charges_externes"]),
                  ("Impôts et taxes", -x["impots_taxes"]), ("Personnel", -x["charges_personnel"]), ("Amortissements", -x["dotations_nettes"])]
        somme = sum(v for _, v in etapes if pd.notna(v)) - (x["impot_benefices"] if pd.notna(x["impot_benefices"]) else 0)
        autres = (x["resultat_net"] - somme) if pd.notna(x["resultat_net"]) else 0
        etapes += [("Autres produits et charges", autres), ("Impôt sur les bénéfices", -x["impot_benefices"])]
        fig = go.Figure(go.Waterfall(x=[e for e, _ in etapes] + ["Résultat net"], y=[v for _, v in etapes] + [0],
                                     measure=["absolute"] + ["relative"] * (len(etapes) - 1) + ["total"],
                                     increasing={"marker": {"color": c.COULEURS[0]}}, decreasing={"marker": {"color": c.COULEURS[2]}},
                                     totals={"marker": {"color": "#A855F7"}}, connector={"line": {"color": "#3B2366"}}))
        vz.graphe(fig, "Du chiffre d'affaires au résultat net", 400)
    with d:
        vz.panneau("Ratios et feux")
        det = R.ratios_detail[R.ratios_detail["company_id"] == x["company_id"]]
        st.markdown(vz.table_ratios(det), unsafe_allow_html=True)

    g, m, d = st.columns(3)
    with g:
        tm = R.tresorerie_mois[R.tresorerie_mois["company_id"] == x["company_id"]]
        fig = go.Figure(go.Scatter(x=tm["mois"], y=tm["solde"], mode="lines", line={"color": "#E879F9", "width": 3, "shape": "spline"},
                                   fill="tozeroy", fillcolor="rgba(168,85,247,0.22)"))
        vz.graphe(fig, "Solde bancaire en fin de mois", 300)
    with m:
        fc = R.factures_clients[(R.factures_clients["company_id"] == x["company_id"]) & R.factures_clients["tranche"].notna()]
        tr = fc.groupby("tranche", observed=False)["reste_a_encaisser"].sum()
        fig = go.Figure(go.Bar(x=tr.index.astype(str), y=tr.values,
                               marker_color=["#2EE59D", "#C4B5FD", "#FFB547", "#F59E6B", "#FF4D6D"]))
        vz.graphe(fig, "Factures clients non encaissées par retard", 300)
    with d:
        fl = R.flux[R.flux["company_id"] == x["company_id"]].sort_values("mois").tail(12)
        fig = go.Figure([go.Bar(x=fl["mois"], y=fl["encaissements"], name="Entrées", marker_color="#2EE59D"),
                         go.Bar(x=fl["mois"], y=fl["decaissements"], name="Sorties", marker_color="#FF4D6D")])
        vz.graphe(fig, "Entrées et sorties d'argent (12 mois)", 300)

    g, d = st.columns([3, 2])
    with g:
        vz.panneau("Factures clients en retard")
        f = fc[fc["jours_retard"] > 0].sort_values("jours_retard", ascending=False)[["client_final", "date_facture", "echeance", "reste_a_encaisser", "jours_retard"]]
        st.dataframe(f, hide_index=True, width="stretch", height=260, column_config={
            "client_final": "Client final", "date_facture": st.column_config.DateColumn("Facture", format="DD/MM/YYYY"),
            "echeance": st.column_config.DateColumn("Échéance", format="DD/MM/YYYY"),
            "reste_a_encaisser": st.column_config.NumberColumn("Reste à encaisser", format="%.0f €"),
            "jours_retard": st.column_config.NumberColumn("Jours de retard", format="%d")})
    with d:
        vz.panneau("Déclarations de TVA")
        tv = R.tva[R.tva["company_id"] == x["company_id"]].sort_values("fin_periode", ascending=False)
        tv = tv.assign(etat=tv["en_retard"].map({True: "🔴 En retard", False: ""}))[["fin_periode", "statut", "montant", "etat"]]
        st.dataframe(tv, hide_index=True, width="stretch", height=260, column_config={
            "fin_periode": st.column_config.DateColumn("Fin de période", format="DD/MM/YYYY"), "statut": "Statut",
            "montant": st.column_config.NumberColumn("Montant", format="%.0f €"), "etat": "Alerte"})


def page_secteur():
    vz.titre("Comparaison sectorielle", "Chaque client face aux autres clients de sa catégorie")
    g, d = st.columns([3, 2])
    with g:
        p = CL.dropna(subset=["ENDETTEMENT", "MARGE_EBE"])
        fig = go.Figure()
        for code in [0, 1, 2, -1]:
            q = p[p["feu_code"] == code]
            fig.add_trace(go.Scatter(x=q["ENDETTEMENT"] * 100, y=q["MARGE_EBE"] * 100, mode="markers", name=c.FEUX[code],
                                     text=q["client"] + "<br>" + q["secteur"], hovertemplate="%{text}<br>Endettement %{x:.0f} %<br>Marge EBE %{y:.1f} %<extra></extra>",
                                     marker={"color": c.COULEURS[code], "size": 9, "opacity": 0.85, "line": {"width": 0}}))
        fig.add_hline(y=2, line_dash="dot", line_color="#FF4D6D", opacity=0.5)
        fig.add_vline(x=200, line_dash="dot", line_color="#FF4D6D", opacity=0.5)
        fig.update_xaxes(title="Taux d'endettement (%)", range=[0, min(400, p["ENDETTEMENT"].max() * 100 + 20)])
        fig.update_yaxes(title="Marge d'EBE (%)")
        vz.graphe(fig, "Marge d'EBE et endettement de chaque client", 620, legende=True)
    with d:
        vz.panneau("Repères par catégorie")
        m = c.mediane_par_secteur(CL).reset_index().rename(columns={"secteur": "Catégorie"})
        m["Marge d'EBE médiane"] *= 100
        m["Endettement médian"] *= 100
        st.dataframe(m, hide_index=True, width="stretch", height=600, column_config={
            "Marge d'EBE médiane": st.column_config.NumberColumn(format="%.1f %%"),
            "Endettement médian": st.column_config.NumberColumn(format="%.0f %%"),
            "Délai clients médian (j)": st.column_config.NumberColumn(format="%d"),
            "Trésorerie médiane (j)": st.column_config.NumberColumn(format="%d")})


def page_tresorerie():
    vz.titre("Trésorerie et BFR", "Soldes bancaires, flux et délais de paiement")
    k = st.columns(5)
    k[0].markdown(vz.carte("Solde bancaire total", c.euros(CL["solde_bancaire"].sum()), "tous comptes visibles"), unsafe_allow_html=True)
    k[1].markdown(vz.carte("Trésorerie tendue", str(int((CL["st_TRESO_JOURS"] == 2).sum())), "clients sous 15 jours"), unsafe_allow_html=True)
    k[2].markdown(vz.carte("Variation sur 12 mois", c.euros(CL["variation_12m"].sum()), "entrées moins sorties"), unsafe_allow_html=True)
    k[3].markdown(vz.carte("Factures à plus de 90 jours", c.euros(CL["encours_90j"].sum()), "côté clients"), unsafe_allow_html=True)
    k[4].markdown(vz.carte("Fournisseurs en retard", c.euros(CL["fournisseurs_retard_60j"].sum()), "plus de 60 jours"), unsafe_allow_html=True)
    g, d = st.columns(2)
    fl = R.flux[R.flux["company_id"].isin(IDS)].groupby("mois")[["encaissements", "decaissements"]].sum().reset_index()
    with g:
        fig = go.Figure([go.Bar(x=fl["mois"], y=fl["encaissements"], name="Entrées", marker_color="#2EE59D"),
                         go.Bar(x=fl["mois"], y=fl["decaissements"], name="Sorties", marker_color="#FF4D6D")])
        vz.graphe(fig, "Entrées et sorties d'argent par mois", 300, legende=True)
    with d:
        tm = R.tresorerie_mois[R.tresorerie_mois["company_id"].isin(IDS)].groupby("mois")["solde"].sum().reset_index()
        fig = go.Figure(go.Scatter(x=tm["mois"], y=tm["solde"], mode="lines+markers", line={"color": "#E879F9", "width": 3, "shape": "spline"}, marker={"size": 8, "color": "#F3EEFF", "line": {"color": "#A855F7", "width": 2}},
                                   fill="tozeroy", fillcolor="rgba(168,85,247,0.22)"))
        vz.graphe(fig, "Solde bancaire total en fin de mois", 300)
    vz.panneau("Trésorerie par client (les plus tendus en premier)")
    t = CL.sort_values("TRESO_JOURS")[["pastille", "client", "courbe_tresorerie", "solde_bancaire", "TRESO_JOURS", "DELAI_CLIENTS", "DELAI_FOURN", "BFR_JOURS"]]
    t = t.copy(); t["TRESO_JOURS"] = t["TRESO_JOURS"].round(0) + 0.0
    st.dataframe(t, hide_index=True, width="stretch", height=420, column_config={
        "pastille": st.column_config.TextColumn("Feu", width="small"), "client": "Client",
        "courbe_tresorerie": st.column_config.LineChartColumn("12 derniers mois", width="medium"),
        "solde_bancaire": st.column_config.NumberColumn("Solde", format="%.0f €"),
        "TRESO_JOURS": st.column_config.NumberColumn("Tréso (jours)", format="%d"),
        "DELAI_CLIENTS": st.column_config.NumberColumn("Délai clients (j)", format="%d"),
        "DELAI_FOURN": st.column_config.NumberColumn("Délai fournisseurs (j)", format="%d"),
        "BFR_JOURS": st.column_config.NumberColumn("BFR (jours de CA)", format="%d")})


def page_conformite():
    vz.titre("Conformité et qualité", "TVA, déclarations fiscales et justificatifs")
    k = st.columns(5)
    k[0].markdown(vz.carte("Clients avec TVA en retard", str(int((CL["nb_tva_retard"] > 0).sum())), f"{int(CL['nb_tva_retard'].sum())} périodes en tout"), unsafe_allow_html=True)
    k[1].markdown(vz.carte("Déclarations rejetées", str(int(CL["nb_rejets"].sum())), "toutes déclarations"), unsafe_allow_html=True)
    k[2].markdown(vz.carte("Banques non synchronisées", str(int(CL["comptes_non_synchro"].sum())), "comptes à reconnecter"), unsafe_allow_html=True)
    psj = R.flux[R.flux["company_id"].isin(IDS)]
    psj = psj[psj["mois"] >= R.date_ref.replace(day=1) - pd.DateOffset(months=3)]
    part = psj["nb_sans_justificatif"].sum() / max(psj["nb_transactions"].sum(), 1)
    k[3].markdown(vz.carte("Transactions sans justificatif", f"{part * 100:.1f} %".replace(".", ","), "3 derniers mois"), unsafe_allow_html=True)
    k[4].markdown(vz.carte("Dossiers peu fiables", str(int((CL["fiabilite"] == "Faible").sum())), "bilan ancien ou banque coupée"), unsafe_allow_html=True)
    a, b, d = st.columns(3)
    with a:
        s = CL.groupby("collaborateur")["nb_tva_retard"].sum().sort_values()
        vz.graphe(go.Figure(go.Bar(x=s.values, y=s.index, orientation="h", marker_color="#FFB547")), "TVA en retard par collaborateur", 300)
    with b:
        dr = R.declarations[R.declarations["company_id"].isin(IDS) & R.declarations["statut"].isin(["rejected", "error"])]
        s = dr.groupby("type_declaration").size().sort_values()
        vz.graphe(go.Figure(go.Bar(x=s.values, y=s.index, orientation="h", marker_color="#FF4D6D")), "Déclarations rejetées par type", 300)
    with d:
        s = CL[CL["fiabilite"] == "Faible"].groupby("secteur").size().sort_values()
        vz.graphe(go.Figure(go.Bar(x=s.values, y=s.index, orientation="h", marker_color="#A855F7")), "Dossiers peu fiables par catégorie", 300)
    vz.panneau("Suivi par dossier")
    t = CL.sort_values(["nb_tva_retard", "nb_rejets"], ascending=False)[
        ["client", "collaborateur", "nb_tva_retard", "nb_rejets", "comptes_non_synchro", "part_sans_justificatif", "age_dernier_bilan_mois", "fiabilite"]].copy()
    t["part_sans_justificatif"] *= 100
    st.dataframe(t, hide_index=True, width="stretch", height=420, column_config={
        "client": "Client", "collaborateur": "Collaborateur", "nb_tva_retard": "TVA en retard", "nb_rejets": "Déclarations rejetées",
        "comptes_non_synchro": "Banques non synchronisées",
        "part_sans_justificatif": st.column_config.NumberColumn("Sans justificatif", format="%.0f %%"),
        "age_dernier_bilan_mois": st.column_config.NumberColumn("Âge dernier bilan (mois)", format="%d"), "fiabilite": "Fiabilité"})


{"Portefeuille": page_portefeuille, "Fiche client": page_fiche, "Comparaison sectorielle": page_secteur,
 "Trésorerie et BFR": page_tresorerie, "Conformité et qualité": page_conformite}[page]()

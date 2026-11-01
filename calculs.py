"""
Calculs du tableau de bord de risque clients (ORBIT).

Ce fichier lit le classeur Excel (même format que le Data Sharing Pennylane)
et calcule, pour chaque client : les soldes, les ratios, les feux,
le score de risque, la trésorerie, les factures, la TVA et la fiabilité.
Les règles sont les mêmes que dans le modèle Power BI.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import date

import numpy as np
import pandas as pd

# ---------------------------------------------------------------------------
# SEUILS D'ALERTE : à valider avec les associés. Modifiez simplement les chiffres.
# sens "bas"  = mauvais quand la valeur est BASSE (rouge si valeur < rouge)
# sens "haut" = mauvais quand la valeur est HAUTE (rouge si valeur > rouge)
# ---------------------------------------------------------------------------
SEUILS = [
    # code,            indicateur,                  famille,       sens,   orange, rouge, unité
    ("MARGE_EBE",      "Marge d'EBE",               "Rentabilité", "bas",  0.05,   0.02,  "%"),
    ("RN_CA",          "Résultat net / CA",         "Rentabilité", "bas",  0.01,   0.0,   "%"),
    ("ENDETTEMENT",    "Taux d'endettement",        "Solidité",    "haut", 1.0,    2.0,   "%"),
    ("AUTONOMIE",      "Autonomie financière",      "Solidité",    "bas",  0.25,   0.15,  "%"),
    ("CAPA_REMB",      "Capacité de remboursement", "Solidité",    "haut", 4.0,    6.0,   "ans"),
    ("LIQUIDITE",      "Ratio de liquidité",        "Liquidité",   "bas",  1.2,    1.0,   "x"),
    ("COUV_INTERETS",  "Couverture des intérêts",   "Liquidité",   "bas",  5.0,    3.0,   "fois"),
    ("TRESO_JOURS",    "Trésorerie en jours",       "Liquidité",   "bas",  30.0,   15.0,  "jours"),
    ("DELAI_CLIENTS",  "Délai clients",             "Délais",      "haut", 60.0,   90.0,  "jours"),
    ("DELAI_FOURN",    "Délai fournisseurs",        "Délais",      "haut", 75.0,   120.0, "jours"),
    ("ROTATION_STOCK", "Rotation des stocks",       "Délais",      "haut", 90.0,   150.0, "jours"),
]
SEUILS_DF = pd.DataFrame(SEUILS, columns=["code", "indicateur", "famille", "sens", "orange", "rouge", "unite"])
CODES = [s[0] for s in SEUILS]

TAUX_TVA = 0.2
FEUX = {2: "Rouge", 1: "Orange", 0: "Vert", -1: "Non évalué"}
COULEURS = {2: "#FF4D6D", 1: "#FFB547", 0: "#2EE59D", -1: "#5B6782"}
EMOJI = {2: "🔴", 1: "🟠", 0: "🟢", -1: "⚪"}

ONGLETS = ["Dim_Client", "Dim_Client_Cabinet", "Fait_Comptes", "Factures_Clients", "Factures_Fournisseurs",
           "Banque_Comptes", "Banque_Flux", "TVA", "Declarations_Fiscales"]
DATES = {
    "Dim_Client": ["date_creation"], "Dim_Client_Cabinet": ["date_depart_prevue"],
    "Fait_Comptes": ["debut_exercice", "fin_exercice", "date_cloture_pennylane"],
    "Factures_Clients": ["date_facture", "echeance"], "Factures_Fournisseurs": ["date_facture", "echeance"],
    "Banque_Comptes": ["derniere_synchro"], "Banque_Flux": ["mois"],
    "TVA": ["debut_periode", "fin_periode"], "Declarations_Fiscales": ["debut_periode", "fin_periode"],
}


# ---------------------------------------------------------------------------
# Lecture
# ---------------------------------------------------------------------------
def charger(source) -> dict[str, pd.DataFrame]:
    """Lit les 9 onglets du classeur (chemin ou fichier envoyé)."""
    feuilles = pd.read_excel(source, sheet_name=None, engine="openpyxl")
    manquants = [o for o in ONGLETS if o not in feuilles and o != "Dim_Client_Cabinet"]
    if manquants:
        raise ValueError("Onglets manquants dans le fichier : " + ", ".join(manquants))
    d = {}
    for o in ONGLETS:
        df = feuilles.get(o, pd.DataFrame()).copy()
        for c in DATES.get(o, []):
            if c in df.columns:
                df[c] = pd.to_datetime(df[c], errors="coerce")
        d[o] = df
    if d["Dim_Client_Cabinet"].empty:
        d["Dim_Client_Cabinet"] = pd.DataFrame({"company_id": d["Dim_Client"]["company_id"], "collaborateur": "Non renseigné"})
    return d


def date_reference(d: dict[str, pd.DataFrame]) -> pd.Timestamp:
    """Aujourd'hui, sans dépasser le mois suivant les dernières données bancaires (utile pour les données fictives)."""
    auj = pd.Timestamp(date.today())
    flux = d["Banque_Flux"]
    if not flux.empty and flux["mois"].notna().any():
        borne = flux["mois"].max() + pd.offsets.MonthEnd(1)
        return min(auj, borne)
    return auj


# ---------------------------------------------------------------------------
# Comptes annuels
# ---------------------------------------------------------------------------
def _rang_cloture(fc: pd.DataFrame) -> pd.DataFrame:
    fc = fc.copy()
    clos = fc["date_cloture_pennylane"].notna()
    fc["rang"] = np.nan
    fc.loc[clos, "rang"] = fc[clos].groupby("company_id")["debut_exercice"].rank(ascending=False, method="first")
    fc["jours"] = (fc["fin_exercice"] - fc["debut_exercice"]).dt.days + 1
    return fc


def _soldes(x: pd.DataFrame) -> pd.DataFrame:
    """Soldes intermédiaires et bilan à partir des postes d'un exercice."""
    s = pd.DataFrame(index=x.index)
    s["ca"] = x["ca"]
    s["valeur_ajoutee"] = x["ca"] + x["autres_produits_expl"] - x["achats_consommes"] - x["charges_externes"]
    s["ebe"] = s["valeur_ajoutee"] - x["impots_taxes"] - x["charges_personnel"]
    s["resultat_exploitation"] = (s["ebe"] + x["reprises_expl"] + x["autres_produits_gestion"]
                                  - x["dotations_expl"] - x["autres_charges_gestion"])
    s["resultat_net"] = x["resultat_net"]
    s["caf"] = x["resultat_net"] + x["dotations_totales"] - x["reprises_totales"] - x["produits_cessions"] + x["vnc_cessions"]
    # À VÉRIFIER sur de vrais dossiers : si Pennylane solde déjà le résultat dans le compte 12, retirez "+ resultat_net".
    s["capitaux_propres"] = x["capitaux_propres_hors_resultat"] + x["resultat_net"]
    s["dettes_financieres"] = x["emprunts"] + x["concours_bancaires"]
    s["emprunts"] = x["emprunts"]
    s["interets"] = x["interets"]
    s["total_actif"] = (x["immo_brutes"] - x["amortissements"] + x["immo_financieres"] + x["stocks"]
                        + x["clients"] + x["autres_creances"] + x["disponibilites"])
    s["dettes_court_terme"] = x["fournisseurs"] + x["dettes_fiscales_sociales"] + x["autres_dettes"] + x["concours_bancaires"]
    s["actif_court_terme"] = x["stocks"] + x["clients"] + x["autres_creances"] + x["disponibilites"]
    s["bfr"] = x["stocks"] + x["clients"] - x["fournisseurs"] - x["dettes_fiscales_sociales"]
    s["fonds_de_roulement"] = s["capitaux_propres"] + x["emprunts"] - (x["immo_brutes"] - x["amortissements"] + x["immo_financieres"])
    s["achats_consommes"] = x["achats_consommes"]
    s["charges_externes"] = x["charges_externes"]
    s["impots_taxes"] = x["impots_taxes"]
    s["charges_personnel"] = x["charges_personnel"]
    s["dotations_nettes"] = x["dotations_totales"] - x["reprises_totales"]
    s["impot_benefices"] = x["impot_benefices"]
    s["stocks"] = x["stocks"]
    s["clients"] = x["clients"]
    s["fournisseurs"] = x["fournisseurs"]
    s["jours"] = x["jours"]
    s["fin_exercice"] = x["fin_exercice"]
    s["debut_exercice"] = x["debut_exercice"]
    return s


def _div(a, b):
    a, b = pd.Series(a, dtype="float64"), pd.Series(b, dtype="float64")
    return a.where(b != 0) / b.where(b != 0)


def _ratios(s: pd.DataFrame) -> pd.DataFrame:
    r = pd.DataFrame(index=s.index)
    ca_pos = s["ca"] > 0
    r["MARGE_EBE"] = _div(s["ebe"], s["ca"]).where(ca_pos)
    r["RN_CA"] = _div(s["resultat_net"], s["ca"]).where(ca_pos)
    r["ENDETTEMENT"] = _div(s["dettes_financieres"], s["capitaux_propres"]).where(s["capitaux_propres"] > 0)
    r["AUTONOMIE"] = _div(s["capitaux_propres"], s["total_actif"])
    r["CAPA_REMB"] = _div(s["dettes_financieres"], s["caf"]).where(s["caf"] > 0)
    r["LIQUIDITE"] = _div(s["actif_court_terme"], s["dettes_court_terme"])
    r["COUV_INTERETS"] = _div(s["ebe"], s["interets"]).where(s["interets"] > 0)
    r["DELAI_CLIENTS"] = (_div(s["clients"], s["ca"] * (1 + TAUX_TVA)) * s["jours"]).where(ca_pos)
    achats = s["achats_consommes"] + s["charges_externes"]
    r["DELAI_FOURN"] = (_div(s["fournisseurs"], achats * (1 + TAUX_TVA)) * s["jours"]).where(achats > 0)
    r["ROTATION_STOCK"] = (_div(s["stocks"], s["achats_consommes"]) * s["jours"]).where((s["stocks"] > 0) & (s["achats_consommes"] > 0))
    r["BFR_JOURS"] = (_div(s["bfr"], s["ca"]) * s["jours"]).where(ca_pos)
    return r


def _statut(v, sens, orange, rouge):
    if v is None or pd.isna(v):
        return np.nan
    if sens == "bas":
        return 2 if v < rouge else 1 if v < orange else 0
    return 2 if v > rouge else 1 if v > orange else 0


def _statuts(r: pd.DataFrame, s: pd.DataFrame) -> pd.DataFrame:
    st = pd.DataFrame(index=r.index)
    for code, _, _, sens, o, rg, _ in SEUILS:
        if code not in r.columns:
            continue
        st[code] = [_statut(v, sens, o, rg) for v in r[code]]
    # Règles particulières (identiques au modèle Power BI)
    cp = s["capitaux_propres"]
    st.loc[cp.notna() & (cp <= 0), "ENDETTEMENT"] = 2
    dettes, caf = s["dettes_financieres"], s["caf"]
    st.loc[caf.notna() & (dettes <= 0), "CAPA_REMB"] = 0
    st.loc[caf.notna() & (dettes > 0) & (caf <= 0), "CAPA_REMB"] = 2
    st.loc[s["ebe"].notna() & r["COUV_INTERETS"].isna(), "COUV_INTERETS"] = 0
    return st


# ---------------------------------------------------------------------------
# Résultat principal
# ---------------------------------------------------------------------------
@dataclass
class Resultats:
    clients: pd.DataFrame          # une ligne par client, tout ce qu'il faut pour les pages
    ratios_detail: pd.DataFrame    # client × ratio : valeur N, N-1, statut
    tresorerie_mois: pd.DataFrame  # client × mois : solde reconstitué
    flux: pd.DataFrame             # flux bancaires mensuels
    factures_clients: pd.DataFrame
    tva: pd.DataFrame
    declarations: pd.DataFrame
    date_ref: pd.Timestamp


def calculer(d: dict[str, pd.DataFrame], rang: int = 1) -> Resultats:
    ref = date_reference(d)
    debut_mois = ref.replace(day=1)
    cl = d["Dim_Client"].merge(d["Dim_Client_Cabinet"][["company_id", "collaborateur"]], on="company_id", how="left")
    cl["collaborateur"] = cl["collaborateur"].fillna("Non renseigné").astype(str).str.split("@").str[0]
    cl["secteur"] = cl["secteur"].fillna("Non renseigné")
    cl = cl.set_index("company_id")

    # --- comptes annuels de l'exercice choisi et du précédent
    fc = _rang_cloture(d["Fait_Comptes"])
    n = fc[fc["rang"] == rang].set_index("company_id")
    n1 = fc[fc["rang"] == rang + 1].set_index("company_id")
    sN, sN1 = _soldes(n), _soldes(n1)

    # --- trésorerie bancaire (donnée du jour)
    bc = d["Banque_Comptes"]
    solde = bc[bc["visible"].astype(bool)].groupby("company_id")["solde"].sum()
    flux = d["Banque_Flux"].copy()
    fen3 = flux[(flux["mois"] >= debut_mois - pd.DateOffset(months=3)) & (flux["mois"] < debut_mois)]
    dec_moy = fen3.groupby("company_id")["decaissements"].sum() / 3
    treso_jours = _div(solde, dec_moy / 30)
    var12 = flux[flux["mois"] >= debut_mois - pd.DateOffset(months=12)].groupby("company_id")["flux_net"].sum()

    # --- ratios et statuts
    rN = _ratios(sN).reindex(cl.index)
    rN["TRESO_JOURS"] = treso_jours.reindex(cl.index)
    rN1 = _ratios(sN1).reindex(cl.index)
    sNr = sN.reindex(cl.index)
    stN = _statuts(rN, sNr)
    # Pas de N-1 pour la trésorerie en jours (donnée du jour)
    rN1["TRESO_JOURS"] = np.nan

    # --- TVA et déclarations
    tva = d["TVA"].copy()
    tva["en_retard"] = (tva["attendue"].astype(bool) & tva["statut"].isin(["not_done", "pending"])
                        & (tva["fin_periode"] < ref - pd.Timedelta(days=30)))
    nb_tva_retard = tva[tva["en_retard"]].groupby("company_id").size().reindex(cl.index, fill_value=0)
    decl = d["Declarations_Fiscales"].copy()
    nb_rejets = decl[decl["statut"].isin(["rejected", "error"])].groupby("company_id").size().reindex(cl.index, fill_value=0)

    # --- feu global et score
    evalues = stN[CODES].notna().sum(axis=1)
    rouges = (stN[CODES] == 2).sum(axis=1)
    oranges = (stN[CODES] == 1).sum(axis=1)
    rouges_feu = rouges + (nb_tva_retard > 0).astype(int)
    feu = np.select([evalues < 3, rouges_feu >= 2, (rouges_feu >= 1) | (oranges >= 2)], [-1, 2, 1], default=0)
    score = np.where(feu >= 0, np.round((2 * rouges + oranges) / (2 * evalues.replace(0, np.nan)) * 100), np.nan)

    # --- raisons du feu (3 principales)
    def libelle(code, v):
        if pd.isna(v) and code == "ENDETTEMENT":
            return "capitaux propres négatifs"
        if pd.isna(v) and code == "CAPA_REMB":
            return "CAF négative"
        u = SEUILS_DF.set_index("code").loc[code, "unite"]
        return format_valeur(v, u)

    raisons = []
    seuils_idx = SEUILS_DF.set_index("code")
    for cid in cl.index:
        lignes = []
        for ordre, code in enumerate(CODES):
            stt = stN.at[cid, code]
            if pd.notna(stt) and stt >= 1:
                sd = seuils_idx.loc[code]
                lignes.append((-stt, ordre, f"{sd['indicateur']} : {libelle(code, rN.at[cid, code])}"))
        lignes = [t for _, _, t in sorted(lignes)[:3]]
        if nb_tva_retard[cid] > 0:
            lignes.append(f"TVA en retard : {nb_tva_retard[cid]} période(s)")
        raisons.append(" · ".join(lignes) if lignes else "Aucun ratio en alerte")

    # --- factures
    fcl = d["Factures_Clients"].copy()
    fcl["jours_retard"] = np.where((fcl["reste_a_encaisser"] > 0) & fcl["echeance"].notna(),
                                   (ref - fcl["echeance"]).dt.days.clip(lower=0), np.nan)
    fcl["tranche"] = pd.cut(fcl["jours_retard"], [-1, 0, 30, 60, 90, 1e9],
                            labels=["Non échue", "1 à 30 jours", "31 à 60 jours", "61 à 90 jours", "Plus de 90 jours"])
    fcl.loc[fcl["reste_a_encaisser"] <= 0, "tranche"] = np.nan
    encours = fcl.groupby("company_id")["reste_a_encaisser"].sum()
    encours90 = fcl[fcl["jours_retard"] > 90].groupby("company_id")["reste_a_encaisser"].sum()
    ff = d["Factures_Fournisseurs"].copy()
    ff_retard = (~ff["payee"].astype(bool)) & ((ref - ff["echeance"]).dt.days > 60)
    fourn60 = ff[ff_retard].groupby("company_id")["montant_ttc"].sum()

    # --- qualité des données
    sync_ko = bc["visible"].astype(bool) & (bc["derniere_synchro"].isna()
                                            | (bc["derniere_synchro"] < ref - pd.Timedelta(days=7))
                                            | (~bc["derniere_synchro_ok"].astype(bool)))
    nb_sync_ko = bc[sync_ko].groupby("company_id").size().reindex(cl.index, fill_value=0)
    f3 = flux[flux["mois"] >= debut_mois - pd.DateOffset(months=3)].groupby("company_id")[["nb_sans_justificatif", "nb_transactions"]].sum()
    part_sans_justif = _div(f3["nb_sans_justificatif"], f3["nb_transactions"]).reindex(cl.index)
    fin_dernier = fc[fc["rang"] == 1].set_index("company_id")["fin_exercice"].reindex(cl.index)
    age_mois = ((ref - fin_dernier).dt.days / 30.44).round()
    fiab = np.select([age_mois.isna() | (age_mois > 18) | (nb_sync_ko > 0), (age_mois > 15) | (part_sans_justif > 0.2)],
                     ["Faible", "Moyenne"], default="Bonne")

    # --- solde reconstitué fin de mois, 12 derniers mois
    mois = [(ref + pd.offsets.MonthEnd(0)) - pd.offsets.MonthEnd(i) for i in range(11, -1, -1)]
    tm = []
    flux_par_client = flux.groupby("company_id")
    for cid in cl.index:
        s0 = solde.get(cid, np.nan)
        if pd.isna(s0):
            continue
        g = flux_par_client.get_group(cid) if cid in flux_par_client.groups else flux.iloc[0:0]
        for m in mois:
            tm.append((cid, m, s0 - g.loc[g["mois"] > m, "flux_net"].sum()))
    tresorerie_mois = pd.DataFrame(tm, columns=["company_id", "mois", "solde"])
    courbes = tresorerie_mois.groupby("company_id")["solde"].apply(list)

    # --- table clients
    out = cl.copy()
    for c in ["ca", "ebe", "resultat_net", "capitaux_propres", "caf", "dettes_financieres", "bfr", "fonds_de_roulement",
              "valeur_ajoutee", "resultat_exploitation", "achats_consommes", "charges_externes", "impots_taxes",
              "charges_personnel", "dotations_nettes", "impot_benefices", "fin_exercice", "debut_exercice"]:
        out[c] = sNr[c]
    out["ca_n1"] = sN1["ca"].reindex(cl.index)
    out["ebe_n1"] = sN1["ebe"].reindex(cl.index)
    out["rn_n1"] = sN1["resultat_net"].reindex(cl.index)
    out["evolution_ca"] = _div(out["ca"] - out["ca_n1"], out["ca_n1"].abs())
    for code in CODES + ["BFR_JOURS"]:
        out[code] = rN[code]
    for code in CODES:
        out["st_" + code] = stN[code]
    out["solde_bancaire"] = solde.reindex(cl.index)
    out["decaissements_mensuels"] = dec_moy.reindex(cl.index)
    out["variation_12m"] = var12.reindex(cl.index)
    out["nb_ratios_evalues"] = evalues
    out["nb_rouges"] = rouges
    out["nb_oranges"] = oranges
    out["feu_code"] = feu
    out["feu"] = out["feu_code"].map(FEUX)
    out["pastille"] = out["feu_code"].map(EMOJI)
    out["score"] = score
    out["raisons"] = raisons
    out["nb_tva_retard"] = nb_tva_retard
    out["nb_rejets"] = nb_rejets
    out["encours_clients"] = encours.reindex(cl.index).fillna(0)
    out["encours_90j"] = encours90.reindex(cl.index).fillna(0)
    out["fournisseurs_retard_60j"] = fourn60.reindex(cl.index).fillna(0)
    out["comptes_non_synchro"] = nb_sync_ko
    out["part_sans_justificatif"] = part_sans_justif
    out["age_dernier_bilan_mois"] = age_mois
    out["fiabilite"] = fiab
    out["courbe_tresorerie"] = courbes.reindex(cl.index)
    out = out.reset_index()

    # --- détail des ratios (fiche client)
    det = []
    for cid in cl.index:
        for code, ind, fam, sens, o, rg, u in SEUILS:
            det.append(dict(company_id=cid, code=code, indicateur=ind, famille=fam, sens=sens, orange=o, rouge=rg, unite=u,
                            valeur=rN.at[cid, code], valeur_n1=rN1.at[cid, code], statut=stN.at[cid, code]))
    ratios_detail = pd.DataFrame(det)

    flux_out = flux.merge(out[["company_id", "collaborateur", "secteur"]], on="company_id", how="left")
    tva_out = tva.merge(out[["company_id", "collaborateur", "secteur"]], on="company_id", how="left")
    decl_out = decl.merge(out[["company_id", "collaborateur", "secteur"]], on="company_id", how="left")
    return Resultats(out, ratios_detail, tresorerie_mois, flux_out, fcl, tva_out, decl_out, ref)


# ---------------------------------------------------------------------------
# Mise en forme
# ---------------------------------------------------------------------------
def format_valeur(v, unite: str) -> str:
    if v is None or pd.isna(v):
        return "–"
    if unite == "%":
        return f"{v * 100:.1f} %".replace(".", ",")
    if unite == "x":
        return f"{v:.2f}".replace(".", ",")
    if unite == "ans":
        return f"{v:.1f} ans".replace(".", ",")
    if unite == "fois":
        return f"{v:.1f} fois".replace(".", ",")
    return f"{v:.0f} j"


def euros(v) -> str:
    if v is None or pd.isna(v):
        return "–"
    a = abs(v)
    if a >= 1e6:
        t = f"{v / 1e6:.1f} M€"
    elif a >= 1e4:
        t = f"{v / 1e3:.0f} k€"
    else:
        t = f"{v:,.0f} €".replace(",", " ")
    return t.replace(".", ",")


def seuil_texte(sens, orange, rouge, unite) -> str:
    o, r = format_valeur(orange, unite), format_valeur(rouge, unite)
    return f"🟠 < {o} · 🔴 < {r}" if sens == "bas" else f"🟠 > {o} · 🔴 > {r}"


def mediane_par_secteur(clients: pd.DataFrame) -> pd.DataFrame:
    g = clients.groupby("secteur")
    return pd.DataFrame({
        "Clients": g.size(),
        "En rouge": g["feu_code"].apply(lambda s: int((s == 2).sum())),
        "Marge d'EBE médiane": g["MARGE_EBE"].median(),
        "Délai clients médian (j)": g["DELAI_CLIENTS"].median(),
        "Endettement médian": g["ENDETTEMENT"].median(),
        "Trésorerie médiane (j)": g["TRESO_JOURS"].median(),
    }).sort_values("Clients", ascending=False)

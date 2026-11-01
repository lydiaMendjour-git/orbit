# ORBIT – Radar des risques clients (prototype Python)

Ce prototype lit l'Excel fictif (même format que le Data Sharing Pennylane), calcule les ratios,
les feux (vert / orange / rouge) et le score de risque, puis affiche le tableau de bord dans ton navigateur.

## 1. Ce qu'il faut avoir sur le PC

- **Python 3.10 ou plus récent.** Pour vérifier, ouvre l'« Invite de commandes » (touche Windows, tape `cmd`) et tape :
  `py --version`
  Si rien ne s'affiche, installe Python depuis python.org et coche **« Add Python to PATH »** pendant l'installation.

## 2. Installer (une seule fois)

1. Dézippe `prototype_python_dbf.zip` où tu veux, par exemple dans `Documents\prototype_python`.
2. Ouvre l'Invite de commandes **dans ce dossier** : dans l'Explorateur, clique dans la barre d'adresse du dossier, tape `cmd` puis Entrée.
3. Tape :

```
py -m pip install -r requirements.txt
```

## 3. Lancer le tableau de bord

Dans la même Invite de commandes :

```
py -m streamlit run app.py
```

Le navigateur s'ouvre tout seul sur http://localhost:8501. Pour arrêter : reviens dans l'Invite de commandes et fais `Ctrl + C`.

La première fois, Streamlit peut demander une adresse e-mail : appuie simplement sur Entrée.

## 4. Les 5 pages

| Page | Ce qu'on y voit |
|---|---|
| Portefeuille | Nombre de clients en rouge / orange / vert, répartition, clients rouges par collaborateur, liste triée par risque avec la raison du feu |
| Fiche client | Jauge de score, chiffres clés, pourquoi le client est en rouge, cascade du résultat, tous les ratios avec leurs seuils, trésorerie, factures en retard, TVA |
| Comparaison sectorielle | Chaque client placé selon endettement et marge, médianes par catégorie |
| Trésorerie et BFR | Flux mensuels, solde bancaire, délais clients et fournisseurs |
| Conformité et qualité | TVA en retard, déclarations, dossiers peu fiables |

En haut : les pages en pilules, puis l'exercice (dernier clôturé ou précédent), les filtres collaborateur et catégorie, et le bouton « Fichier ».

## 5. Les données

- Par défaut, le fichier lu est `donnees\donnees_fictives_data_sharing.xlsx`.
- Tu peux aussi charger un autre Excel **au même format** avec le bouton « 📂 Fichier » en haut à droite.

## 6. Changer les seuils des feux

Ouvre `calculs.py` avec le Bloc-notes (ou VS Code). Tout en haut, la liste `SEUILS` contient pour chaque ratio
le seuil orange et le seuil rouge. Modifie le chiffre, enregistre, puis clique sur « Rerun » en haut à droite de la page.

## 7. Contenu du dossier

- `app.py` : les pages du tableau de bord
- `calculs.py` : lecture de l'Excel, ratios, feux, score (mêmes règles que le modèle Power BI)
- `visuels.py` : le thème violet, les animations, les cartes et les images animées (le nom ORBIT se change tout en haut)
- `.streamlit\config.toml` : le thème de Streamlit (dossier caché, à garder)
- `requirements.txt` : les bibliothèques à installer
- `donnees\` : l'Excel fictif

## 8. Plus tard : brancher le vrai Data Sharing

Le prototype lit des feuilles Excel qui portent le nom des requêtes Power BI. Pour passer aux vraies données,
il suffira de remplacer la lecture de l'Excel (fonction `charger` dans `calculs.py`) par une lecture de la base
Pennylane avec tes identifiants, le reste du code ne change pas.

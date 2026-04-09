# 💊 Dashboard Médicaments BDPM

Pipeline data end-to-end sur la **Base de Données Publique des Médicaments** française (ANSM · HAS · UNCAM).

**[🔴 Demo live →]([https://saralld.github.io/Pipeline-automatisation-BDD-publique-du-m-dicament/)**

---

## Ce que fait ce projet

| Composant | Fichier | Rôle | Techno |
|---|---|---|---|
| Scraper | `scraper.py` | Télécharge les CSV officiels BDPM, stocke en SQLite | Python · requests · pandas |
| Scheduler | `scheduler.py` | Mises à jour automatiques 2× par jour | APScheduler |
| API Backend | `main.py` | Expose les données via REST | FastAPI · uvicorn |
| Dashboard | `index.html` | Visualisation interactive 6 pages | Chart.js · HTML/CSS/JS |
| Base de données | `data/medicaments.db` | Stockage persistant | SQLite |

## Données couvertes (15 800+ médicaments)

- ✅ Spécialités pharmaceutiques + statut AMM
- ✅ Prix & taux de remboursement Sécu
- ✅ Compositions & substances actives
- ✅ Groupes génériques
- ✅ Alertes & retraits de marché (ANSM)
- ✅ Évaluations HAS (SMR / ASMR)

## Pages du dashboard

| Page | Contenu |
|---|---|
| **Vue d'ensemble** | KPIs globaux, répartition AMM, formes, remboursement |
| **Médicaments** | Recherche par nom, filtre statut/labo |
| **Laboratoires** | Génériqueurs vs non-génériqueurs, ratio par labo |
| **AMM & Indications** | Évolution temporelle par année et par laboratoire |
| **Prix & Remboursement** | Taux Sécu, prix moyens par catégorie |
| **Alertes & Retraits** | Timeline des informations importantes ANSM |
| **Pipeline & Logs** | État du scheduler, historique des exécutions |

---

## Stack technique

```
Python 3.11 · FastAPI · SQLite · APScheduler
requests · pandas · Chart.js 4
GitHub Pages · Render
```

## Source des données

- [base-donnees-publique.medicaments.gouv.fr](https://base-donnees-publique.medicaments.gouv.fr)
- Licence : Licence Ouverte / Open Licence (Etalab)
- Producteur : ANSM · HAS · UNCAM · Ministère de la Santé

---

*Dashboard Médicaments BDPM v1.0 · Sara LLD · 2026*

# 💊 Dashboard Médicaments BDPM

Pipeline data end-to-end sur la **Base de Données Publique des Médicaments** française (ANSM · HAS · UNCAM).

**[🔴 Demo live →](https://SaraLLD.github.io/NOM-DU-REPO)**

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

## 🚀 Déploiement en 2 étapes

### Étape 1 — Backend sur Render (gratuit)

1. Va sur [render.com](https://render.com) → **New Web Service**
2. Connecte ton repo GitHub
3. Configure :
   - **Build command** : `pip install -r requirements.txt`
   - **Start command** : `uvicorn main:app --host 0.0.0.0 --port $PORT`
4. Clique **Deploy**
5. Copie ton URL Render (ex: `https://ton-app.onrender.com`)

### Étape 2 — Mettre à jour l'URL dans index.html

Ouvre `index.html`, ligne ~210 :
```javascript
const API = 'https://TON-URL.onrender.com';
```

Remplace par ton URL Render, puis commit & push.

### Étape 3 — Dashboard sur GitHub Pages

1. **Settings → Pages**
2. Branch : `main` · Folder : `/ (root)`
3. **Save**
4. Ton dashboard est live sur : `https://SaraLLD.github.io/NOM-DU-REPO`

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

"""
Backend FastAPI - Dashboard Médicaments BDPM
Routes : stats, médicaments, labos, génériques, AMM, alertes, prix
"""
import sqlite3, os, logging
from fastapi import FastAPI, Query
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
from scheduler import start_scheduler
from scraper import scrape_all, init_db, DB_PATH

log = logging.getLogger(__name__)

@asynccontextmanager
async def lifespan(app: FastAPI):
    init_db()
    # Premier scraping au démarrage si la base est vide
    conn = sqlite3.connect(DB_PATH)
    count = conn.execute("SELECT COUNT(*) FROM specialites").fetchone()[0]
    conn.close()
    if count == 0:
        log.info("Base vide — scraping lancé en arrière-plan...")
        import threading
        threading.Thread(target=scrape_all, daemon=True).start()
    start_scheduler()
    yield

app = FastAPI(
    title="Dashboard Médicaments BDPM",
    description="API analytique sur la Base de Données Publique des Médicaments française",
    version="1.0.0",
    lifespan=lifespan
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

def get_conn():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


# ─────────────────────────────────────────────
# STATS GÉNÉRALES
# ─────────────────────────────────────────────

@app.get("/api/stats")
def stats():
    conn = get_conn()
    total_med    = conn.execute("SELECT COUNT(*) FROM specialites").fetchone()[0]
    total_avec   = conn.execute("SELECT COUNT(*) FROM specialites WHERE etat_commercialisation='Commercialisée'").fetchone()[0]
    total_retrait = conn.execute("SELECT COUNT(*) FROM alertes").fetchone()[0]
    total_labos  = conn.execute("SELECT COUNT(DISTINCT titulaire) FROM specialites WHERE titulaire IS NOT NULL").fetchone()[0]
    total_generiques = conn.execute("SELECT COUNT(DISTINCT id_groupe) FROM generiques").fetchone()[0]
    rembourses   = conn.execute("""
        SELECT COUNT(DISTINCT cis) FROM presentations
        WHERE taux_remboursement IS NOT NULL AND taux_remboursement != ''
    """).fetchone()[0]
    last_update  = conn.execute("SELECT MAX(executed_at) FROM scrape_log WHERE status='OK'").fetchone()[0]
    conn.close()
    return {
        "total_medicaments": total_med,
        "commercialises": total_avec,
        "alertes_retraits": total_retrait,
        "laboratoires": total_labos,
        "groupes_generiques": total_generiques,
        "rembourses_secu": rembourses,
        "derniere_maj": last_update
    }


# ─────────────────────────────────────────────
# MÉDICAMENTS — recherche & détail
# ─────────────────────────────────────────────

@app.get("/api/medicaments")
def liste_medicaments(
    q: str = Query(None, description="Recherche par nom"),
    statut: str = Query(None, description="Filtre statut AMM"),
    etat: str = Query(None, description="Filtre état commercialisation"),
    titulaire: str = Query(None, description="Filtre laboratoire"),
    limit: int = Query(100, le=500),
    offset: int = 0
):
    conn = get_conn()
    sql = "SELECT * FROM specialites WHERE 1=1"
    params = []
    if q:
        sql += " AND denomination LIKE ?"
        params.append(f"%{q}%")
    if statut:
        sql += " AND statut_amm = ?"
        params.append(statut)
    if etat:
        sql += " AND etat_commercialisation = ?"
        params.append(etat)
    if titulaire:
        sql += " AND titulaire LIKE ?"
        params.append(f"%{titulaire}%")
    sql += " ORDER BY denomination LIMIT ? OFFSET ?"
    params += [limit, offset]
    rows = conn.execute(sql, params).fetchall()
    conn.close()
    return [dict(r) for r in rows]


@app.get("/api/medicaments/{cis}")
def detail_medicament(cis: str):
    conn = get_conn()
    med = conn.execute("SELECT * FROM specialites WHERE cis=?", (cis,)).fetchone()
    if not med:
        return {"error": "Médicament non trouvé"}
    presentations = conn.execute("SELECT * FROM presentations WHERE cis=?", (cis,)).fetchall()
    compositions  = conn.execute("SELECT * FROM compositions WHERE cis=?", (cis,)).fetchall()
    generique     = conn.execute("SELECT * FROM generiques WHERE cis=?", (cis,)).fetchall()
    alertes       = conn.execute("SELECT * FROM alertes WHERE cis=?", (cis,)).fetchall()
    smr           = conn.execute("SELECT * FROM smr WHERE cis=?", (cis,)).fetchall()
    asmr          = conn.execute("SELECT * FROM asmr WHERE cis=?", (cis,)).fetchall()
    conn.close()
    return {
        "specialite": dict(med),
        "presentations": [dict(r) for r in presentations],
        "compositions":  [dict(r) for r in compositions],
        "generiques":    [dict(r) for r in generique],
        "alertes":       [dict(r) for r in alertes],
        "smr":           [dict(r) for r in smr],
        "asmr":          [dict(r) for r in asmr],
    }


# ─────────────────────────────────────────────
# LABORATOIRES — génériques vs non-génériques
# ─────────────────────────────────────────────

@app.get("/api/labos/generiques")
def labos_generiques(top: int = Query(30, le=100)):
    """
    Retourne pour chaque laboratoire :
    - nb de médicaments développés
    - nb dans un groupe générique
    - nb hors générique
    - ratio générique (%)
    """
    conn = get_conn()
    rows = conn.execute("""
        SELECT
            s.titulaire                              AS laboratoire,
            COUNT(DISTINCT s.cis)                    AS total_medicaments,
            COUNT(DISTINCT g.cis)                    AS avec_generique,
            COUNT(DISTINCT s.cis) - COUNT(DISTINCT g.cis) AS sans_generique,
            ROUND(
                100.0 * COUNT(DISTINCT g.cis) / COUNT(DISTINCT s.cis), 1
            )                                        AS ratio_generique_pct
        FROM specialites s
        LEFT JOIN generiques g ON s.cis = g.cis
        WHERE s.titulaire IS NOT NULL AND s.titulaire != ''
        GROUP BY s.titulaire
        HAVING total_medicaments >= 3
        ORDER BY total_medicaments DESC
        LIMIT ?
    """, (top,)).fetchall()
    conn.close()
    return [dict(r) for r in rows]


@app.get("/api/labos/stats")
def labos_stats():
    """Répartition globale : labos génériqueurs vs non-génériqueurs"""
    conn = get_conn()
    rows = conn.execute("""
        SELECT
            CASE WHEN g.cis IS NOT NULL THEN 'Développe des génériques'
                 ELSE 'Pas de génériques' END AS categorie,
            COUNT(DISTINCT s.titulaire) AS nb_laboratoires,
            COUNT(DISTINCT s.cis)       AS nb_medicaments
        FROM specialites s
        LEFT JOIN generiques g ON s.cis = g.cis
        WHERE s.titulaire IS NOT NULL
        GROUP BY categorie
    """).fetchall()
    conn.close()
    return [dict(r) for r in rows]


# ─────────────────────────────────────────────
# AMM PAR INDICATION ET PAR LABORATOIRE
# ─────────────────────────────────────────────

@app.get("/api/amm/par-annee")
def amm_par_annee():
    """Évolution du nombre d'AMM accordées par année"""
    conn = get_conn()
    rows = conn.execute("""
        SELECT
            SUBSTR(date_amm, -4) AS annee,
            COUNT(*)             AS nb_amm
        FROM specialites
        WHERE date_amm IS NOT NULL
          AND SUBSTR(date_amm,-4) GLOB '[0-9][0-9][0-9][0-9]'
          AND CAST(SUBSTR(date_amm,-4) AS INTEGER) >= 1990
        GROUP BY annee
        ORDER BY annee
    """).fetchall()
    conn.close()
    return [dict(r) for r in rows]


@app.get("/api/amm/par-labo-annee")
def amm_par_labo_annee(top_labos: int = Query(10, le=30)):
    """
    Pour les N premiers labos (par volume),
    retourne leur historique d'AMM année par année.
    Utile pour le graphique évolution AMM par labo.
    """
    conn = get_conn()
    # Récupérer les top labos
    top = conn.execute("""
        SELECT titulaire, COUNT(*) as nb
        FROM specialites
        WHERE titulaire IS NOT NULL AND titulaire != ''
        GROUP BY titulaire
        ORDER BY nb DESC
        LIMIT ?
    """, (top_labos,)).fetchall()
    top_noms = [r["titulaire"] for r in top]

    placeholders = ",".join("?" * len(top_noms))
    rows = conn.execute(f"""
        SELECT
            titulaire,
            SUBSTR(date_amm, -4) AS annee,
            COUNT(*)             AS nb_amm
        FROM specialites
        WHERE titulaire IN ({placeholders})
          AND date_amm IS NOT NULL
          AND SUBSTR(date_amm,-4) GLOB '[0-9][0-9][0-9][0-9]'
          AND CAST(SUBSTR(date_amm,-4) AS INTEGER) >= 1995
        GROUP BY titulaire, annee
        ORDER BY annee, titulaire
    """, top_noms).fetchall()
    conn.close()
    return {"labos": top_noms, "data": [dict(r) for r in rows]}


@app.get("/api/amm/par-forme")
def amm_par_forme():
    """Répartition des AMM par forme pharmaceutique"""
    conn = get_conn()
    rows = conn.execute("""
        SELECT forme_pharma, COUNT(*) AS nb
        FROM specialites
        WHERE forme_pharma IS NOT NULL
        GROUP BY forme_pharma
        ORDER BY nb DESC
        LIMIT 20
    """).fetchall()
    conn.close()
    return [dict(r) for r in rows]


@app.get("/api/amm/par-type")
def amm_par_type():
    """Répartition par type d'AMM (nationale, européenne, etc.)"""
    conn = get_conn()
    rows = conn.execute("""
        SELECT type_amm, statut_amm, COUNT(*) AS nb
        FROM specialites
        WHERE type_amm IS NOT NULL
        GROUP BY type_amm, statut_amm
        ORDER BY nb DESC
    """).fetchall()
    conn.close()
    return [dict(r) for r in rows]


# ─────────────────────────────────────────────
# PRIX & REMBOURSEMENT
# ─────────────────────────────────────────────

@app.get("/api/prix/remboursement")
def remboursement_stats():
    """Répartition par taux de remboursement"""
    conn = get_conn()
    rows = conn.execute("""
        SELECT
            taux_remboursement,
            COUNT(*) AS nb_presentations,
            COUNT(DISTINCT cis) AS nb_medicaments
        FROM presentations
        WHERE taux_remboursement IS NOT NULL AND taux_remboursement != ''
        GROUP BY taux_remboursement
        ORDER BY nb_presentations DESC
    """).fetchall()
    conn.close()
    return [dict(r) for r in rows]


@app.get("/api/prix/stats")
def prix_stats():
    """Statistiques de prix par taux de remboursement"""
    conn = get_conn()
    rows = conn.execute("""
        SELECT
            taux_remboursement,
            COUNT(*) AS nb,
            ROUND(AVG(CAST(REPLACE(prix_sans_honoraires,',','.') AS REAL)),2) AS prix_moyen,
            ROUND(MIN(CAST(REPLACE(prix_sans_honoraires,',','.') AS REAL)),2) AS prix_min,
            ROUND(MAX(CAST(REPLACE(prix_sans_honoraires,',','.') AS REAL)),2) AS prix_max
        FROM presentations
        WHERE prix_sans_honoraires IS NOT NULL
          AND prix_sans_honoraires != ''
          AND taux_remboursement IS NOT NULL
        GROUP BY taux_remboursement
        ORDER BY nb DESC
    """).fetchall()
    conn.close()
    return [dict(r) for r in rows]


# ─────────────────────────────────────────────
# ALERTES & RETRAITS
# ─────────────────────────────────────────────

@app.get("/api/alertes")
def liste_alertes(limit: int = Query(100, le=500)):
    conn = get_conn()
    rows = conn.execute("""
        SELECT a.*, s.denomination, s.titulaire, s.etat_commercialisation
        FROM alertes a
        LEFT JOIN specialites s ON a.cis = s.cis
        ORDER BY a.id DESC
        LIMIT ?
    """, (limit,)).fetchall()
    conn.close()
    return [dict(r) for r in rows]


@app.get("/api/alertes/par-type")
def alertes_par_type():
    conn = get_conn()
    rows = conn.execute("""
        SELECT type_info, COUNT(*) AS nb
        FROM alertes
        WHERE type_info IS NOT NULL
        GROUP BY type_info
        ORDER BY nb DESC
    """).fetchall()
    conn.close()
    return [dict(r) for r in rows]


# ─────────────────────────────────────────────
# GÉNÉRIQUES
# ─────────────────────────────────────────────

@app.get("/api/generiques/groupes")
def groupes_generiques(limit: int = Query(50, le=200)):
    conn = get_conn()
    rows = conn.execute("""
        SELECT g.id_groupe, g.libelle_groupe,
               COUNT(DISTINCT g.cis) AS nb_medicaments,
               GROUP_CONCAT(DISTINCT s.titulaire) AS laboratoires
        FROM generiques g
        LEFT JOIN specialites s ON g.cis = s.cis
        GROUP BY g.id_groupe
        ORDER BY nb_medicaments DESC
        LIMIT ?
    """, (limit,)).fetchall()
    conn.close()
    return [dict(r) for r in rows]


# ─────────────────────────────────────────────
# SCRAPING MANUEL & LOGS
# ─────────────────────────────────────────────

@app.post("/api/scrape/trigger")
def trigger_scrape():
    import threading
    t = threading.Thread(target=scrape_all, daemon=True)
    t.start()
    return {"status": "scraping lancé en arrière-plan"}


@app.get("/api/scrape/logs")
def scrape_logs(limit: int = 50):
    conn = get_conn()
    rows = conn.execute(
        "SELECT * FROM scrape_log ORDER BY id DESC LIMIT ?", (limit,)
    ).fetchall()
    conn.close()
    return [dict(r) for r in rows]

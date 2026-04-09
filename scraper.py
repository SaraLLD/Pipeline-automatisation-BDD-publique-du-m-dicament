"""
Scraper - Base de Données Publique des Médicaments (BDPM)
Source : base-donnees-publique.medicaments.gouv.fr
"""
import sqlite3, requests, pandas as pd, logging, os
from datetime import datetime
from io import StringIO

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
log = logging.getLogger(__name__)

DB_PATH = os.environ.get("DB_PATH", "data/medicaments.db")
BASE_URL = "https://base-donnees-publique.medicaments.gouv.fr/telechargement.php?fichier="

FICHIERS = {
    "specialites":   "CIS_bdpm.txt",
    "presentations": "CIS_CIP_bdpm.txt",
    "compositions":  "CIS_COMPO_bdpm.txt",
    "generiques":    "CIS_GENER_bdpm.txt",
    "alertes":       "CIS_InfoImportantes.txt",
    "smr":           "CIS_HAS_SMR_bdpm.txt",
    "asmr":          "CIS_HAS_ASMR_bdpm.txt",
}

COLONNES = {
    "specialites":   ["cis","denomination","forme_pharma","voies_admin","statut_amm","type_amm","etat_commercialisation","date_amm","statut_bdm","numero_autorisation_europeenne","titulaire","surveillance_renforcee"],
    "presentations": ["cis","cip7","libelle","statut_admin","etat_commercialisation","date_declaration_commercialisation","cip13","agrement_collectivites","taux_remboursement","prix_sans_honoraires","prix_avec_honoraires","prix_honoraires","indications_remboursement"],
    "compositions":  ["cis","designation_elem_pharma","code_substance","denomination_substance","dosage","ref_dosage","nature_composant","numero_liaison"],
    "generiques":    ["id_groupe","libelle_groupe","cis","type_generique","numero_tri"],
    "alertes":       ["cis","type_info","lien_html"],
    "smr":           ["cis","code_dossier_has","motif_evaluation","date_avis_commission","valeur_smr","libelle_smr"],
    "asmr":          ["cis","code_dossier_has","motif_evaluation","date_avis_commission","valeur_asmr","libelle_asmr"],
}

DDL = """
CREATE TABLE IF NOT EXISTS specialites (
    cis TEXT PRIMARY KEY, denomination TEXT, forme_pharma TEXT,
    voies_admin TEXT, statut_amm TEXT, type_amm TEXT,
    etat_commercialisation TEXT, date_amm TEXT, statut_bdm TEXT,
    numero_autorisation_europeenne TEXT, titulaire TEXT,
    surveillance_renforcee TEXT, updated_at TEXT
);
CREATE TABLE IF NOT EXISTS presentations (
    cip13 TEXT PRIMARY KEY, cis TEXT, cip7 TEXT, libelle TEXT,
    statut_admin TEXT, etat_commercialisation TEXT,
    date_declaration_commercialisation TEXT, agrement_collectivites TEXT,
    taux_remboursement TEXT, prix_sans_honoraires TEXT,
    prix_avec_honoraires TEXT, prix_honoraires TEXT,
    indications_remboursement TEXT, updated_at TEXT
);
CREATE TABLE IF NOT EXISTS compositions (
    id INTEGER PRIMARY KEY AUTOINCREMENT, cis TEXT,
    designation_elem_pharma TEXT, code_substance TEXT,
    denomination_substance TEXT, dosage TEXT, ref_dosage TEXT,
    nature_composant TEXT, numero_liaison TEXT, updated_at TEXT
);
CREATE TABLE IF NOT EXISTS generiques (
    id INTEGER PRIMARY KEY AUTOINCREMENT, id_groupe TEXT,
    libelle_groupe TEXT, cis TEXT, type_generique TEXT,
    numero_tri TEXT, updated_at TEXT
);
CREATE TABLE IF NOT EXISTS alertes (
    id INTEGER PRIMARY KEY AUTOINCREMENT, cis TEXT,
    type_info TEXT, lien_html TEXT, updated_at TEXT
);
CREATE TABLE IF NOT EXISTS smr (
    id INTEGER PRIMARY KEY AUTOINCREMENT, cis TEXT,
    code_dossier_has TEXT, motif_evaluation TEXT,
    date_avis_commission TEXT, valeur_smr TEXT,
    libelle_smr TEXT, updated_at TEXT
);
CREATE TABLE IF NOT EXISTS asmr (
    id INTEGER PRIMARY KEY AUTOINCREMENT, cis TEXT,
    code_dossier_has TEXT, motif_evaluation TEXT,
    date_avis_commission TEXT, valeur_asmr TEXT,
    libelle_asmr TEXT, updated_at TEXT
);
CREATE TABLE IF NOT EXISTS scrape_log (
    id INTEGER PRIMARY KEY AUTOINCREMENT, table_name TEXT,
    rows_inserted INTEGER, status TEXT, message TEXT, executed_at TEXT
);
"""

def init_db():
    os.makedirs("data", exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    conn.executescript(DDL)
    conn.commit()
    conn.close()
    log.info("DB initialisée.")

def telecharger(nom_fichier):
    url = BASE_URL + nom_fichier
    try:
        r = requests.get(url, timeout=60)
        r.raise_for_status()
        content = r.content.decode("utf-8", errors="replace")
        df = pd.read_csv(StringIO(content), sep="\t", header=None, dtype=str, quoting=3, on_bad_lines="skip")
        log.info(f"  ✓ {nom_fichier} → {len(df)} lignes")
        return df
    except Exception as e:
        log.error(f"  ✗ {nom_fichier}: {e}")
        return None

def inserer(conn, table, df, colonnes):
    now = datetime.utcnow().isoformat()
    df = df.copy()
    nb = len(colonnes)
    df = df.iloc[:, :nb] if len(df.columns) > nb else df
    while len(df.columns) < nb:
        df[len(df.columns)] = None
    df.columns = colonnes
    df["updated_at"] = now

    if table in ("specialites", "presentations"):
        tmp = f"{table}_tmp"
        df.to_sql(tmp, conn, if_exists="replace", index=False)
        conn.execute(f"INSERT OR REPLACE INTO {table} SELECT * FROM {tmp}")
        conn.execute(f"DROP TABLE IF EXISTS {tmp}")
    else:
        conn.execute(f"DELETE FROM {table}")
        df.to_sql(table, conn, if_exists="append", index=False)

    conn.execute(
        "INSERT INTO scrape_log (table_name,rows_inserted,status,executed_at) VALUES (?,?,'OK',?)",
        (table, len(df), now)
    )
    conn.commit()
    log.info(f"  → {table}: {len(df)} lignes insérées")

def scrape_all():
    log.info("=== Scraping BDPM démarré ===")
    init_db()
    conn = sqlite3.connect(DB_PATH)
    for table, fichier in FICHIERS.items():
        log.info(f"[{table}] {fichier}")
        df = telecharger(fichier)
        if df is not None:
            inserer(conn, table, df, COLONNES[table])
    conn.close()
    log.info("=== Scraping terminé ===")

if __name__ == "__main__":
    scrape_all()

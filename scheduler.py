"""
Scheduler - Mises à jour automatiques BDPM
"""
from apscheduler.schedulers.background import BackgroundScheduler
from scraper import scrape_all
import logging

log = logging.getLogger(__name__)

def start_scheduler():
    scheduler = BackgroundScheduler(timezone="UTC")
    # Scraping mensuel le 1er de chaque mois à 7h00 UTC
    # (la BDPM publie ses mises à jour vers le 30 du mois précédent)
    scheduler.add_job(scrape_all, "cron", day=1, hour=7, minute=0, id="scrape_monthly")
    scheduler.start()
    log.info("Scheduler démarré : scraping mensuel le 1er du mois à 7h00 UTC.")
    return scheduler

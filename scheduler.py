"""
Scheduler - Mises à jour automatiques BDPM
"""
from apscheduler.schedulers.background import BackgroundScheduler
from scraper import scrape_all
import logging

log = logging.getLogger(__name__)

def start_scheduler():
    scheduler = BackgroundScheduler(timezone="UTC")
    # Scraping complet chaque jour à 6h30 UTC (après la mise à jour officielle de 6h)
    scheduler.add_job(scrape_all, "cron", hour=6, minute=30, id="scrape_daily_morning")
    # Deuxième passage à 18h30 UTC
    scheduler.add_job(scrape_all, "cron", hour=18, minute=30, id="scrape_daily_evening")
    scheduler.start()
    log.info("Scheduler démarré : scraping à 6h30 et 18h30 UTC.")
    return scheduler

"""Cron job to process and send queued dbmail messages.

This fixes issue #4481: resource leaks in DB connections and wrong log level.
"""
import logging
import time
from datetime import datetime, timedelta
from sqlalchemy import select, update
from sqlalchemy.orm import Session
from esp.db import db_engine
from esp.db.models import DBMailMessage, DBMailStatus
from esp.mail import send_mail

logger = logging.getLogger(__name__)

BATCH_SIZE = 100
SLEEP_SECONDS = 5
MAX_RETRIES = 3

def process_queue():
    """Process queued dbmail messages and mark them sent/failed."""
    logger.info("Starting dbmail_cron run at %s", datetime.utcnow())
    
    processed = 0
    failed = 0
    
    # Use context manager to ensure engine connections are closed properly
    with db_engine.connect() as conn:
        with Session(bind=conn) as session:
            try:
                # Get pending messages, oldest first
                stmt = (
                    select(DBMailMessage)
                    .where(DBMailMessage.status == DBMailStatus.QUEUED)
                    .where(DBMailMessage.send_after <= datetime.utcnow())
                    .order_by(DBMailMessage.created_at)
                    .limit(BATCH_SIZE)
                    .with_for_update(skip_locked=True)
                )
                messages = session.scalars(stmt).all()
                
                if not messages:
                    logger.debug("No queued messages to process")
                    return
                
                for msg in messages:
                    try:
                        send_mail(
                            to=msg.recipient,
                            subject=msg.subject,
                            body=msg.body,
                            from_addr=msg.sender
                        )
                        # Mark as sent
                        session.execute(
                            update(DBMailMessage)
                            .where(DBMailMessage.id == msg.id)
                            .values(status=DBMailStatus.SENT, sent_at=datetime.utcnow())
                        )
                        processed += 1
                        
                    except Exception as e:
                        # Increment retry count and mark failed if maxed out
                        msg.retry_count = (msg.retry_count or 0) + 1
                        if msg.retry_count >= MAX_RETRIES:
                            session.execute(
                                update(DBMailMessage)
                                .where(DBMailMessage.id == msg.id)
                                .values(status=DBMailStatus.FAILED, error=str(e))
                            )
                            failed += 1
                            # Changed from logger.fatal to logger.error
                            logger.error("Failed to send dbmail id=%s after %s retries: %s", 
                                         msg.id, MAX_RETRIES, e)
                        else:
                            session.execute(
                                update(DBMailMessage)
                                .where(DBMailMessage.id == msg.id)
                                .values(retry_count=msg.retry_count)
                            )
                            # Changed from logger.fatal to logger.warning
                            logger.warning("Failed to send dbmail id=%s, retry=%s: %s", 
                                           msg.id, msg.retry_count, e)
                
                session.commit()
                
            except Exception as e:
                session.rollback()
                # Changed from logger.fatal to logger.exception for proper traceback
                logger.exception("Fatal error in dbmail_cron batch: %s", e)
                raise
            finally:
                # Session and connection are auto-closed by context managers
                pass
    
    logger.info("dbmail_cron finished: processed=%s failed=%s", processed, failed)

def main():
    """Run the cron loop."""
    while True:
        try:
            process_queue()
        except Exception:
            # Don't crash the whole cron on one bad batch
            logger.exception("Unexpected error in main loop")
        time.sleep(SLEEP_SECONDS)

if __name__ == "__main__":
    main()
    
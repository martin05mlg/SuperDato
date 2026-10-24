import asyncio
import io
import uuid
from datetime import datetime, timezone
from typing import Any, Dict, Optional
from celery import shared_task
from sqlalchemy import select
from app.core.celery_app import celery_app
from app.core.database import async_session_maker
from app.domains.integrations.client import GoogleOAuthClient
from app.domains.integrations.models import GoogleAccountConnection, ImportJob
from app.domains.receipts.extractor.pdf_parser import PDFReceiptExtractor
from app.domains.receipts.services import ReceiptService


def run_async(coro):
    """Helper to run async coroutines inside sync Celery task worker threads."""
    try:
        loop = asyncio.get_event_loop()
    except RuntimeError:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
    return loop.run_until_complete(coro)


@celery_app.task(bind=True, max_retries=3, default_retry_delay=60)
def sync_google_connection_task(self, connection_id_str: str) -> Dict[str, Any]:
    """Celery background task to synchronize Mercadona tickets from a connected Google account."""
    return run_async(_async_sync_connection(connection_id_str))


async def _async_sync_connection(connection_id_str: str) -> Dict[str, Any]:
    connection_id = uuid.UUID(connection_id_str)

    async with async_session_maker() as db:
        res = await db.execute(
            select(GoogleAccountConnection).where(GoogleAccountConnection.id == connection_id)
        )
        conn = res.scalar_one_or_none()
        if not conn:
            return {"error": f"Connection {connection_id_str} not found"}

        # Create ImportJob record
        job = ImportJob(
            household_id=conn.household_id,
            connection_id=conn.id,
            source_type="GMAIL_PERIODIC",
            status="PROCESSING",
            started_at=datetime.now(timezone.utc),
        )
        db.add(job)
        conn.sync_status = "SYNCING"
        await db.commit()
        await db.refresh(job)

        try:
            from app.domains.admin.services import AdminService
            client_id, client_secret, _ = await AdminService.get_effective_google_config(db)

            # 1. Get valid access token (refreshes ONLY if expired)
            access_token, updated_enc = await GoogleOAuthClient.get_valid_access_token(
                conn.encrypted_tokens,
                client_id=client_id,
                client_secret=client_secret,
            )
            if updated_enc != conn.encrypted_tokens:
                conn.encrypted_tokens = updated_enc
                await db.commit()

            # 2. Search messages
            messages = await GoogleOAuthClient.search_mercadona_messages(access_token)
            job.messages_found = len(messages)
            await db.commit()

            # Determine destination household & status based on user's household count
            target_household_id = conn.household_id
            target_assignment_status = "ASSIGNED"

            if conn.user_id:
                from app.domains.households.models import HouseholdMembership
                hh_mems_stmt = select(HouseholdMembership).where(HouseholdMembership.user_id == conn.user_id)
                mems = (await db.execute(hh_mems_stmt)).scalars().all()
                if len(mems) > 1:
                    target_household_id = None
                    target_assignment_status = "PENDING_ASSIGNMENT"

            # 3. Process messages
            for msg in messages:
                msg_id = msg.get("id")
                try:
                    pdf_bytes = await GoogleOAuthClient.fetch_pdf_attachment(access_token, msg_id)
                    if not pdf_bytes:
                        continue

                    stream = io.BytesIO(pdf_bytes)
                    extracted = PDFReceiptExtractor.extract_from_stream(stream)

                    # Save to DB & memory with deduplication check
                    saved = await ReceiptService.save_extracted_receipt_to_db(
                        db=db,
                        extracted=extracted,
                        household_id=target_household_id,
                        import_job_id=job.id,
                        imported_by_user_id=conn.user_id,
                        assignment_status=target_assignment_status,
                    )
                    if saved:
                        job.receipts_imported += 1
                    else:
                        job.receipts_skipped += 1

                except Exception as ex:
                    job.errors_count += 1
                    job.error_details.append({
                        "message_id": msg_id,
                        "error": str(ex),
                        "timestamp": datetime.now(timezone.utc).isoformat(),
                    })

            # Mark completed
            job.status = "COMPLETED"
            job.completed_at = datetime.now(timezone.utc)
            conn.sync_status = "IDLE"
            conn.last_sync_at = datetime.now(timezone.utc)
            conn.last_error = None
            await db.commit()

            return {
                "job_id": str(job.id),
                "messages_found": job.messages_found,
                "imported": job.receipts_imported,
                "skipped": job.receipts_skipped,
                "errors": job.errors_count,
            }

        except Exception as e:
            err_msg = str(e).strip() if str(e).strip() else f"{type(e).__name__}: {repr(e)}"
            logger.exception("Error executing sync for connection %s: %s", connection_id_str, err_msg)
            job.status = "FAILED"
            job.completed_at = datetime.now(timezone.utc)
            job.error_details.append({"general_error": err_msg})
            conn.sync_status = "ERROR"
            conn.last_error = err_msg
            await db.commit()
            return {
                "job_id": str(job.id),
                "error": err_msg,
                "messages_found": 0,
                "imported": 0,
                "skipped": 0,
                "errors": 1,
            }


@celery_app.task
def sync_all_active_google_connections() -> int:
    """Periodic task executed by Celery Beat every 30 minutes to scan all connected Gmail accounts."""
    return run_async(_async_sync_all())


async def _async_sync_all() -> int:
    async with async_session_maker() as db:
        res = await db.execute(
            select(GoogleAccountConnection.id).where(
                GoogleAccountConnection.sync_status.in_(["IDLE", "ERROR"])
            )
        )
        conn_ids = res.scalars().all()

        count = 0
        for cid in conn_ids:
            sync_google_connection_task.delay(str(cid))
            count += 1
        return count

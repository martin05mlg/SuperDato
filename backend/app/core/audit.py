"""Registro de auditoría de acciones administrativas (sin datos sensibles)."""
import logging
from typing import Any, Optional

audit_logger = logging.getLogger("superdato.audit")


def audit(action: str, actor: Optional[Any] = None, target: Optional[str] = None, **extra: Any) -> None:
    """Escribe una línea de auditoría estructurada: quién hizo qué sobre qué."""
    actor_label = getattr(actor, "email", None) or str(actor) if actor else "system"
    details = " ".join(f"{k}={v}" for k, v in extra.items())
    audit_logger.info("AUDIT action=%s actor=%s target=%s %s", action, actor_label, target or "-", details)


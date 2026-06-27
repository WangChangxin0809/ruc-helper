"""
全局设置路由 — SMTP 配置等
"""
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from ..database import get_db
from ..models import Setting
from ..services.grade import reload_email_config

router = APIRouter(prefix="/api/settings", tags=["settings"])

DEFAULT_SMTP = {
    "smtpHost": "smtp.qq.com",
    "smtpPort": "587",
    "smtpUsername": "",
    "smtpPassword": "",
    "fromAddress": "",
}


@router.get("/smtp")
def get_smtp(db: Session = Depends(get_db)):
    result = {}
    for k, default in DEFAULT_SMTP.items():
        s = db.query(Setting).filter(Setting.key == k).first()
        result[k] = s.value if s else default
    return result


@router.put("/smtp")
def set_smtp(
    smtpHost: str = "",
    smtpPort: str = "",
    smtpUsername: str = "",
    smtpPassword: str = "",
    fromAddress: str = "",
    db: Session = Depends(get_db),
):
    updates = {
        "smtpHost": smtpHost,
        "smtpPort": smtpPort,
        "smtpUsername": smtpUsername,
        "smtpPassword": smtpPassword,
        "fromAddress": fromAddress,
    }
    for k, v in updates.items():
        if v:
            s = db.query(Setting).filter(Setting.key == k).first()
            if s:
                s.value = v
            else:
                db.add(Setting(key=k, value=v))
    db.commit()
    reload_email_config()
    return {"message": "SMTP 配置已更新", "config": {k: v or "(未设置)" for k, v in updates.items()}}

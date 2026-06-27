"""
学生管理路由
"""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from ..database import get_db
from ..models import Student, Grade, now
from ..schemas import StudentCreate, StudentResponse, MessageResponse
from ..services.auth import do_login, encrypt_password

router = APIRouter(prefix="/api/students", tags=["students"])


def _to_response(s: Student, db: Session) -> StudentResponse:
    count = db.query(Grade).filter(Grade.student_id == s.student_id).count()
    last_grade = (
        db.query(Grade).filter(Grade.student_id == s.student_id)
        .order_by(Grade.last_updated_at.desc()).first()
    )
    return StudentResponse(
        id=s.id,
        student_id=s.student_id,
        name=s.name,
        email=s.email,
        major=s.major,
        grade=s.grade,
        is_active=s.is_active,
        is_monitored=s.is_monitored,
        token_expires_at=s.token_expires_at,
        grade_count=count,
        last_change_at=last_grade.last_updated_at if last_grade else None,
        created_at=s.created_at,
    )


@router.post("/", response_model=StudentResponse)
def add_student(body: StudentCreate, db: Session = Depends(get_db)):
    existing = db.query(Student).filter(Student.student_id == body.student_id).first()
    if existing:
        raise HTTPException(400, "该学生已存在")

    result = do_login(body.student_id, body.password)
    if not result:
        raise HTTPException(400, "登录失败，请检查学号和密码")

    student = Student(
        student_id=body.student_id,
        name=result["authcode"],
        password=encrypt_password(body.password),
        email=body.email,
        res_token=result["resToken"],
        session=result["session"],
        authcode=result["authcode"],
        token_expires_at=result["token_expires_at"],
    )
    db.add(student)
    db.commit()
    db.refresh(student)
    return _to_response(student, db)


@router.get("/", response_model=list[StudentResponse])
def list_students(db: Session = Depends(get_db)):
    return [_to_response(s, db) for s in db.query(Student).all()]


@router.get("/{student_id}", response_model=StudentResponse)
def get_student(student_id: str, db: Session = Depends(get_db)):
    s = db.query(Student).filter(Student.student_id == student_id).first()
    if not s:
        raise HTTPException(404, "学生不存在")
    return _to_response(s, db)


@router.delete("/{student_id}", response_model=MessageResponse)
def delete_student(student_id: str, db: Session = Depends(get_db)):
    s = db.query(Student).filter(Student.student_id == student_id).first()
    if not s:
        raise HTTPException(404, "学生不存在")
    db.delete(s)
    db.commit()
    return MessageResponse(message=f"已删除 {student_id}")


@router.post("/{student_id}/relogin", response_model=MessageResponse)
def relogin_student(student_id: str, db: Session = Depends(get_db)):
    s = db.query(Student).filter(Student.student_id == student_id).first()
    if not s:
        raise HTTPException(404, "学生不存在")

    from ..services.auth import decrypt_password
    password = decrypt_password(s.password)
    result = do_login(student_id, password)
    if not result:
        raise HTTPException(400, "重新登录失败")

    s.res_token = result["resToken"]
    s.session = result["session"]
    s.authcode = result["authcode"]
    s.token_expires_at = result["token_expires_at"]
    if not s.name or s.name == student_id:
        s.name = result["authcode"]
    s.updated_at = now()
    db.commit()

    return MessageResponse(message=f"{student_id} 重新登录成功")


@router.post("/{student_id}/monitor", response_model=StudentResponse)
def toggle_monitor(student_id: str, db: Session = Depends(get_db)):
    s = db.query(Student).filter(Student.student_id == student_id).first()
    if not s:
        raise HTTPException(404, "学生不存在")
    s.is_monitored = not s.is_monitored
    db.commit()
    return _to_response(s, db)


@router.post("/{student_id}/test-email", response_model=MessageResponse)
def test_email(student_id: str, db: Session = Depends(get_db)):
    s = db.query(Student).filter(Student.student_id == student_id).first()
    if not s:
        raise HTTPException(404, "学生不存在")
    if not s.email:
        raise HTTPException(400, "该学生未设置通知邮箱")

    from ..services.grade import send_grade_email
    from ..models import Grade
    grades = db.query(Grade).filter(Grade.student_id == student_id).all()
    ok = send_grade_email(s.email, s.name or student_id, grades[:1], [])
    if ok:
        return MessageResponse(message=f"测试邮件已发送至 {s.email}")
    raise HTTPException(500, "邮件发送失败，请检查 SMTP 配置")


@router.put("/{student_id}/email", response_model=StudentResponse)
def update_email(student_id: str, email: str = "", db: Session = Depends(get_db)):
    s = db.query(Student).filter(Student.student_id == student_id).first()
    if not s:
        raise HTTPException(404, "学生不存在")
    s.email = email
    db.commit()
    return _to_response(s, db)

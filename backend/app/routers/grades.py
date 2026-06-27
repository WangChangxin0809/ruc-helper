"""
成绩查询路由
"""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from ..database import get_db
from ..models import Student, Grade
from ..schemas import GradeResponse, GradeRefreshResult
from ..services.grade import fetch_grades_from_api, sync_grades, _grade_to_response

router = APIRouter(prefix="/api/grades", tags=["grades"])


@router.get("/{student_id}", response_model=list[GradeResponse])
def get_grades(student_id: str, db: Session = Depends(get_db)):
    student = db.query(Student).filter(Student.student_id == student_id).first()
    if not student:
        raise HTTPException(404, "学生不存在")

    grades = db.query(Grade).filter(Grade.student_id == student_id)\
        .order_by(Grade.semester.desc(), Grade.course_name).all()
    return [_grade_to_response(g) for g in grades]


@router.post("/{student_id}/refresh", response_model=GradeRefreshResult)
def refresh_grades(student_id: str, db: Session = Depends(get_db)):
    student = db.query(Student).filter(Student.student_id == student_id).first()
    if not student:
        raise HTTPException(404, "学生不存在")

    raw = fetch_grades_from_api(student.res_token, student.session, student.authcode)
    if raw is None:
        raise HTTPException(502, "拉取成绩失败，请尝试重新登录")

    result = sync_grades(db, student, raw)

    return GradeRefreshResult(
        student_id=student_id,
        total=result["total"],
        new_count=result["new_count"],
        updated_count=result["updated_count"],
        new_grades=[_grade_to_response(g, is_new=True) for g in result["new_grades"]],
        updated_grades=[_grade_to_response(g) for g in result["updated_grades"]],
    )

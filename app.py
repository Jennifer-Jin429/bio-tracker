from fastapi import FastAPI, Depends, HTTPException, Query
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session, joinedload
from sqlalchemy import func
from datetime import datetime, timedelta
import re
import os

from database import get_db, engine
from models import Base, Class, Student, HomeworkRecord, HomeworkDetail, Dictation
from schemas import *

Base.metadata.create_all(bind=engine)

app = FastAPI(title="生物学情管理平台", version="1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.mount("/static", StaticFiles(directory="static"), name="static")

@app.get("/")
def root():
    return {"message": "生物学情管理平台 API", "docs": "/docs"}

@app.get("/api/classes", response_model=List[ClassWithStudents])
def get_classes(db: Session = Depends(get_db)):
    classes = db.query(Class).options(joinedload(Class.students)).all()
    result = []
    for cls in classes:
        result.append({
            "id": cls.id,
            "name": cls.name,
            "grade": cls.grade,
            "students": [{"id": s.id, "class_id": s.class_id, "student_no": s.student_no, 
                         "name": s.name, "gender": s.gender, "remark": s.remark} for s in cls.students if s.is_active]
        })
    return result

@app.get("/api/students", response_model=List[StudentOut])
def get_students(class_id: int = Query(None), db: Session = Depends(get_db)):
    q = db.query(Student).filter(Student.is_active == 1)
    if class_id:
        q = q.filter(Student.class_id == class_id)
    return q.all()

@app.post("/api/homework", response_model=HomeworkRecordOut)
def create_homework(data: HomeworkCreate, db: Session = Depends(get_db)):
    existing = db.query(HomeworkRecord).filter(
        HomeworkRecord.date == data.date,
        HomeworkRecord.class_id == data.class_id
    ).first()
    if existing:
        raise HTTPException(400, "该班级今日作业已存在")
    
    hw = HomeworkRecord(date=data.date, class_id=data.class_id, title=data.title, remark=data.remark)
    db.add(hw)
    db.commit()
    db.refresh(hw)
    
    students = db.query(Student).filter(Student.class_id == data.class_id, Student.is_active == 1).all()
    for s in students:
        detail = HomeworkDetail(homework_id=hw.id, student_id=s.id, submit_status="已交")
        db.add(detail)
    db.commit()
    db.refresh(hw)
    
    return format_homework(hw)

def format_homework(hw):
    return {
        "id": hw.id,
        "date": hw.date,
        "class_id": hw.class_id,
        "class_name": hw.class_.name if hw.class_ else "",
        "title": hw.title,
        "remark": hw.remark,
        "details": [{
            "id": d.id,
            "homework_id": d.homework_id,
            "student_id": d.student_id,
            "student_no": d.student.student_no,
            "student_name": d.student.name,
            "submit_status": d.submit_status,
            "review_status": d.review_status,
            "review_note": d.review_note,
            "correction_status": d.correction_status,
            "is_resolved": d.is_resolved,
            "resolved_at": d.resolved_at
        } for d in hw.details]
    }

@app.get("/api/homework", response_model=List[HomeworkRecordOut])
def get_homework(class_id: int = Query(...), date: str = Query(None), db: Session = Depends(get_db)):
    q = db.query(HomeworkRecord).filter(HomeworkRecord.class_id == class_id)
    if date:
        q = q.filter(HomeworkRecord.date == date)
    records = q.order_by(HomeworkRecord.date.desc()).all()
    return [format_homework(r) for r in records]

@app.get("/api/homework/{hw_id}/stats")
def get_homework_stats(hw_id: int, db: Session = Depends(get_db)):
    details = db.query(HomeworkDetail).filter(HomeworkDetail.homework_id == hw_id).all()
    total = len(details)
    submitted = sum(1 for d in details if d.submit_status == "已交")
    missing = sum(1 for d in details if d.submit_status == "没交")
    sick = sum(1 for d in details if d.submit_status == "病假")
    empty = sum(1 for d in details if d.submit_status == "没做")
    rate = round(submitted / total * 100, 1) if total > 0 else 0
    return {"total": total, "submitted": submitted, "missing": missing, "sick": sick, "empty": empty, "rate": rate}

@app.put("/api/homework/{hw_id}/details/{detail_id}")
def update_detail(hw_id: int, detail_id: int, data: HomeworkDetailUpdate, db: Session = Depends(get_db)):
    detail = db.query(HomeworkDetail).filter(HomeworkDetail.id == detail_id, HomeworkDetail.homework_id == hw_id).first()
    if not detail:
        raise HTTPException(404, "记录不存在")
    detail.submit_status = data.submit_status
    detail.review_status = data.review_status
    detail.review_note = data.review_note
    detail.correction_status = data.correction_status
    db.commit()
    return {"ok": True}

@app.post("/api/parse", response_model=ParseResponse)
def parse_text(data: ParseRequest, db: Session = Depends(get_db)):
    text = data.text.strip()
    class_id = data.class_id
    homework_id = data.homework_id
    
    students = db.query(Student).filter(Student.class_id == class_id, Student.is_active == 1).all()
    student_map = {s.student_no: s for s in students}
    name_map = {s.name: s for s in students}
    
    success = []
    failed = []
    
    parts = re.split(r'[,，;；\n]', text)
    
    for part in parts:
        part = part.strip()
        if not part:
            continue
        
        match = re.match(r'(.*?)(没交|没做|病假|已交|漏做|需订正|已订正|补做|补交)', part)
        if not match:
            failed.append(f"无法解析：{part}")
            continue
        
        identifier = match.group(1).strip()
        action = match.group(2).strip()
        
        student = None
        clean_id = identifier.replace("号", "").strip()
        if clean_id in student_map:
            student = student_map[clean_id]
        elif identifier in name_map:
            student = name_map[identifier]
        else:
            for s in students:
                if clean_id in s.student_no or clean_id in s.name:
                    student = s
                    break
        
        if not student:
            failed.append(f"未找到学生：{identifier}")
            continue
        
        detail = db.query(HomeworkDetail).filter(
            HomeworkDetail.homework_id == homework_id,
            HomeworkDetail.student_id == student.id
        ).first()
        
        if not detail:
            failed.append(f"{student.name} 无作业记录")
            continue
        
        status_map = {
            "没交": ("没交", ""),
            "没做": ("没做", ""),
            "病假": ("病假", ""),
            "已交": ("已交", ""),
            "漏做": ("已交", "漏做需补"),
            "需订正": ("已交", "需订正"),
            "已订正": ("已交", "已订正"),
            "补做": ("已交", ""),
            "补交": ("已交", ""),
        }
        
        submit_status, review_status = status_map.get(action, ("已交", ""))
        detail.submit_status = submit_status
        if review_status:
            detail.review_status = review_status
        
        if action in ["已交", "已订正", "补做", "补交"]:
            detail.is_resolved = 1
            detail.resolved_at = datetime.now().strftime("%Y-%m-%d %H:%M")
        
        db.commit()
        
        success.append(ParseResult(
            student_id=student.id,
            student_no=student.student_no,
            student_name=student.name,
            action=action,
            detail=f"提交状态->{submit_status}"
        ))
    
    return {"success": success, "failed": failed}

@app.get("/api/todos", response_model=List[TodoItem])
def get_todos(class_id: int = Query(None), db: Session = Depends(get_db)):
    today = datetime.now().strftime("%Y-%m-%d")
    yesterday = (datetime.now() - timedelta(days=1)).strftime("%Y-%m-%d")
    before_yesterday = (datetime.now() - timedelta(days=2)).strftime("%Y-%m-%d")
    
    todos = []
    
    q = db.query(HomeworkDetail, HomeworkRecord).join(HomeworkRecord).filter(
        HomeworkDetail.is_resolved == 0
    )
    if class_id:
        q = q.filter(HomeworkRecord.class_id == class_id)
    
    for detail, hw in q.all():
        overdue = (datetime.now() - datetime.strptime(hw.date, "%Y-%m-%d")).days
        
        if detail.submit_status == "没交":
            type_ = "待补交"
            status = "未补交"
            detail_text = f"{hw.date}作业没交"
        elif detail.submit_status == "没做":
            type_ = "待补做"
            status = "未补做"
            detail_text = f"{hw.date}作业交了空白本子"
        elif detail.submit_status == "病假":
            type_ = "待补交"
            status = "病假中"
            detail_text = f"{hw.date}作业病假未交"
        elif detail.review_status in ["需订正", "漏做需补"]:
            if detail.review_status == "需订正":
                type_ = "待订正"
                status = detail.correction_status or "未订正"
                detail_text = detail.review_note or "需订正"
            else:
                type_ = "待补做"
                status = detail.correction_status or "未补做"
                detail_text = detail.review_note or "漏做需补"
        else:
            continue
        
        if hw.date == today:
            group = "今天"
        elif hw.date == yesterday:
            group = "昨天"
        elif hw.date == before_yesterday:
            group = "前天"
        elif hw.date < before_yesterday:
            group = "更早"
        else:
            continue
        
        todos.append(TodoItem(
            id=detail.id,
            date_group=group,
            student_id=detail.student_id,
            student_no=detail.student.student_no,
            student_name=detail.student.name,
            type=type_,
            source=hw.title,
            detail=detail_text,
            overdue_days=overdue,
            status=status,
            homework_detail_id=detail.id,
            dictation_id=None,
            remark=""
        ))
    
    q2 = db.query(Dictation).filter(Dictation.status.in_(["待重默", "已重默未通过"]))
    if class_id:
        q2 = q2.filter(Dictation.class_id == class_id)
    
    for d in q2.all():
        overdue = (datetime.now() - datetime.strptime(d.date, "%Y-%m-%d")).days
        
        if d.date == today:
            group = "今天"
        elif d.date == yesterday:
            group = "昨天"
        elif d.date == before_yesterday:
            group = "前天"
        elif d.date < before_yesterday:
            group = "更早"
        else:
            group = "昨天"
        
        todos.append(TodoItem(
            id=d.id + 10000,
            date_group=group,
            student_id=d.student_id,
            student_no=d.student.student_no,
            student_name=d.student.name,
            type="待重默",
            source=d.title,
            detail=d.error_content,
            overdue_days=overdue,
            status=d.status,
            homework_detail_id=None,
            dictation_id=d.id,
            remark=d.remark
        ))
    
    group_order = {"今天": 0, "昨天": 1, "前天": 2, "更早": 3}
    todos.sort(key=lambda x: (group_order.get(x.date_group, 4), x.student_id))
    
    return todos

@app.put("/api/todos/resolve")
def resolve_todo(data: TodoResolve, db: Session = Depends(get_db)):
    if data.item_type == "homework":
        detail = db.query(HomeworkDetail).filter(HomeworkDetail.id == data.item_id).first()
        if not detail:
            raise HTTPException(404, "记录不存在")
        detail.is_resolved = 1
        detail.resolved_at = datetime.now().strftime("%Y-%m-%d %H:%M")
        if data.action in ["已订正"]:
            detail.correction_status = "已订正"
        elif data.action in ["已补做", "已补交"]:
            detail.correction_status = "已补做" if data.action == "已补做" else "已补交"
            detail.submit_status = "已交"
        db.commit()
        return {"ok": True}
    
    elif data.item_type == "dictation":
        d = db.query(Dictation).filter(Dictation.id == data.item_id).first()
        if not d:
            raise HTTPException(404, "记录不存在")
        d.status = "已重默通过" if data.action == "已重默" else "已重默未通过"
        d.retest_date = datetime.now().strftime("%Y-%m-%d")
        db.commit()
        return {"ok": True}
    
    return {"ok": False}

@app.post("/api/dictations")
def create_dictation(data: DictationCreate, db: Session = Depends(get_db)):
    d = Dictation(
        date=data.date, class_id=data.class_id, title=data.title,
        student_id=data.student_id, error_content=data.error_content,
        remark=data.remark
    )
    db.add(d)
    db.commit()
    db.refresh(d)
    return {"id": d.id}

@app.get("/api/dictations", response_model=List[DictationOut])
def get_dictations(class_id: int = Query(None), status: str = Query(None), db: Session = Depends(get_db)):
    q = db.query(Dictation)
    if class_id:
        q = q.filter(Dictation.class_id == class_id)
    if status:
        q = q.filter(Dictation.status == status)
    records = q.order_by(Dictation.date.desc()).all()
    return [{
        "id": r.id, "date": r.date, "class_id": r.class_id, "class_name": r.class_.name if r.class_ else "",
        "title": r.title, "student_id": r.student_id, "student_no": r.student.student_no,
        "student_name": r.student.name, "error_content": r.error_content,
        "status": r.status, "retest_date": r.retest_date, "remark": r.remark
    } for r in records]

@app.put("/api/dictations/{id}")
def update_dictation(id: int, data: DictationUpdate, db: Session = Depends(get_db)):
    d = db.query(Dictation).filter(Dictation.id == id).first()
    if not d:
        raise HTTPException(404, "记录不存在")
    d.status = data.status
    if data.retest_date:
        d.retest_date = data.retest_date
    db.commit()
    return {"ok": True}

@app.get("/api/stats/risk")
def get_risk_students(class_id: int = Query(None), db: Session = Depends(get_db)):
    q = db.query(Student)
    if class_id:
        q = q.filter(Student.class_id == class_id)
    students = q.filter(Student.is_active == 1).all()
    
    result = []
    for s in students:
        details = db.query(HomeworkDetail).join(HomeworkRecord).filter(
            HomeworkDetail.student_id == s.id
        ).all()
        
        total_missing = sum(1 for d in details if d.submit_status == "没交")
        total_empty = sum(1 for d in details if d.submit_status == "没做")
        pending_correct = sum(1 for d in details if d.review_status == "需订正" and d.is_resolved == 0)
        
        dictations = db.query(Dictation).filter(Dictation.student_id == s.id, Dictation.status.in_(["待重默", "已重默未通过"])).all()
        pending_dictation = len(dictations)
        
        overdue = sum(1 for d in details if d.is_resolved == 0 and d.submit_status in ["没交", "没做"])
        
        total_issues = total_missing + total_empty + pending_correct + pending_dictation + overdue
        
        if total_issues >= 5:
            risk = "🔴 高风险"
            suggestion = "必须家长沟通"
        elif total_issues >= 2:
            risk = "🟡 关注"
            suggestion = "需督促"
        elif total_issues > 0:
            risk = "🟢 一般"
            suggestion = "及时跟进"
        else:
            continue
        
        result.append({
            "student_id": s.id,
            "student_no": s.student_no,
            "name": s.name,
            "total_missing": total_missing,
            "total_empty": total_empty,
            "pending_correct": pending_correct,
            "pending_dictation": pending_dictation,
            "overdue_count": overdue,
            "risk_level": risk,
            "suggestion": suggestion
        })
    
    result.sort(key=lambda x: x["total_missing"] + x["total_empty"] + x["pending_correct"] + x["pending_dictation"], reverse=True)
    return result

@app.get("/api/stats/overview")
def get_overview(class_id: int = Query(None), db: Session = Depends(get_db)):
    today = datetime.now().strftime("%Y-%m-%d")
    yesterday = (datetime.now() - timedelta(days=1)).strftime("%Y-%m-%d")
    
    q = db.query(HomeworkRecord)
    if class_id:
        q = q.filter(HomeworkRecord.class_id == class_id)
    today_hw = q.filter(HomeworkRecord.date == today).first()
    
    today_missing = 0
    today_empty = 0
    today_sick = 0
    if today_hw:
        for d in today_hw.details:
            if d.submit_status == "没交": today_missing += 1
            elif d.submit_status == "没做": today_empty += 1
            elif d.submit_status == "病假": today_sick += 1
    
    q2 = db.query(HomeworkDetail).join(HomeworkRecord).filter(HomeworkDetail.is_resolved == 0)
    q3 = db.query(Dictation).filter(Dictation.status.in_(["待重默", "已重默未通过"]))
    if class_id:
        q2 = q2.filter(HomeworkRecord.class_id == class_id)
        q3 = q3.filter(Dictation.class_id == class_id)
    
    pending_correct = q2.filter(HomeworkDetail.review_status == "需订正").count()
    pending_dictation = q3.count()
    
    before_yesterday = (datetime.now() - timedelta(days=2)).strftime("%Y-%m-%d")
    overdue_hw = q2.join(HomeworkRecord).filter(HomeworkRecord.date <= before_yesterday).count()
    overdue_dict = q3.filter(Dictation.date <= before_yesterday).count()
    
    return {
        "today_missing": today_missing,
        "today_empty": today_empty,
        "today_sick": today_sick,
        "pending_correct": pending_correct,
        "pending_dictation": pending_dictation,
        "overdue_total": overdue_hw + overdue_dict,
        "today_hw_id": today_hw.id if today_hw else None
    }

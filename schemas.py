from pydantic import BaseModel
from typing import List, Optional

class ClassOut(BaseModel):
    id: int
    name: str
    grade: str
    class Config:
        from_attributes = True

class StudentOut(BaseModel):
    id: int
    class_id: int
    student_no: str
    name: str
    gender: str
    remark: str
    class Config:
        from_attributes = True

class ClassWithStudents(ClassOut):
    students: List[StudentOut]

class HomeworkCreate(BaseModel):
    date: str
    class_id: int
    title: str
    remark: str = ""

class HomeworkDetailUpdate(BaseModel):
    student_id: int
    submit_status: str = "已交"
    review_status: str = ""
    review_note: str = ""
    correction_status: str = ""

class HomeworkDetailOut(BaseModel):
    id: int
    homework_id: int
    student_id: int
    student_no: str
    student_name: str
    submit_status: str
    review_status: str
    review_note: str
    correction_status: str
    is_resolved: int
    resolved_at: str
    class Config:
        from_attributes = True

class HomeworkRecordOut(BaseModel):
    id: int
    date: str
    class_id: int
    class_name: str
    title: str
    remark: str
    details: List[HomeworkDetailOut]
    class Config:
        from_attributes = True

class ParseRequest(BaseModel):
    text: str
    class_id: int
    homework_id: int

class ParseResult(BaseModel):
    student_id: int
    student_no: str
    student_name: str
    action: str
    detail: str

class ParseResponse(BaseModel):
    success: List[ParseResult]
    failed: List[str]

class DictationCreate(BaseModel):
    date: str
    class_id: int
    title: str
    student_id: int
    error_content: str
    remark: str = ""

class DictationOut(BaseModel):
    id: int
    date: str
    class_id: int
    class_name: str
    title: str
    student_id: int
    student_no: str
    student_name: str
    error_content: str
    status: str
    retest_date: str
    remark: str
    class Config:
        from_attributes = True

class DictationUpdate(BaseModel):
    status: str
    retest_date: str = ""

class TodoItem(BaseModel):
    id: int
    date_group: str
    student_id: int
    student_no: str
    student_name: str
    type: str
    source: str
    detail: str
    overdue_days: int
    status: str
    homework_detail_id: Optional[int] = None
    dictation_id: Optional[int] = None
    remark: str

class TodoResolve(BaseModel):
    item_type: str
    item_id: int
    action: str

class StudentRisk(BaseModel):
    student_id: int
    student_no: str
    name: str
    total_missing: int
    total_empty: int
    pending_correct: int
    pending_dictation: int
    overdue_count: int
    risk_level: str
    suggestion: str

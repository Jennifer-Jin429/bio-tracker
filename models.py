from sqlalchemy import Column, Integer, String, Text, ForeignKey, DateTime, func
from sqlalchemy.orm import relationship
from database import Base

class Class(Base):
    __tablename__ = "classes"
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, nullable=False)
    grade = Column(String, default="高二")
    created_at = Column(DateTime, server_default=func.now())
    students = relationship("Student", back_populates="class_", lazy="selectin")

class Student(Base):
    __tablename__ = "students"
    id = Column(Integer, primary_key=True, index=True)
    class_id = Column(Integer, ForeignKey("classes.id"), nullable=False)
    student_no = Column(String, nullable=False)
    name = Column(String, nullable=False)
    gender = Column(String, default="")
    parent_phone = Column(String, default="")
    remark = Column(String, default="")
    is_active = Column(Integer, default=1)
    class_ = relationship("Class", back_populates="students")
    homework_details = relationship("HomeworkDetail", back_populates="student", lazy="selectin")
    dictations = relationship("Dictation", back_populates="student", lazy="selectin")

class HomeworkRecord(Base):
    __tablename__ = "homework_records"
    id = Column(Integer, primary_key=True, index=True)
    date = Column(String, nullable=False)
    class_id = Column(Integer, ForeignKey("classes.id"), nullable=False)
    title = Column(String, nullable=False)
    remark = Column(String, default="")
    created_at = Column(DateTime, server_default=func.now())
    class_ = relationship("Class", lazy="selectin")
    details = relationship("HomeworkDetail", back_populates="homework", lazy="selectin", cascade="all, delete-orphan")

class HomeworkDetail(Base):
    __tablename__ = "homework_details"
    id = Column(Integer, primary_key=True, index=True)
    homework_id = Column(Integer, ForeignKey("homework_records.id"), nullable=False)
    student_id = Column(Integer, ForeignKey("students.id"), nullable=False)
    submit_status = Column(String, default="已交")
    review_status = Column(String, default="")
    review_note = Column(String, default="")
    correction_status = Column(String, default="")
    is_resolved = Column(Integer, default=0)
    resolved_at = Column(String, default="")
    homework = relationship("HomeworkRecord", back_populates="details")
    student = relationship("Student", back_populates="homework_details")

class Dictation(Base):
    __tablename__ = "dictations"
    id = Column(Integer, primary_key=True, index=True)
    date = Column(String, nullable=False)
    class_id = Column(Integer, ForeignKey("classes.id"), nullable=False)
    title = Column(String, nullable=False)
    student_id = Column(Integer, ForeignKey("students.id"), nullable=False)
    error_content = Column(String, default="")
    status = Column(String, default="待重默")
    retest_date = Column(String, default="")
    remark = Column(String, default="")
    created_at = Column(DateTime, server_default=func.now())
    student = relationship("Student", lazy="selectin")
    class_ = relationship("Class", lazy="selectin")

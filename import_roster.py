import pandas as pd
from database import engine, SessionLocal
from models import Base, Class, Student

def init_db():
    Base.metadata.create_all(bind=engine)

def import_roster():
    init_db()
    db = SessionLocal()
    
    db.query(Student).delete()
    db.query(Class).delete()
    db.commit()
    
    df = pd.read_excel("学生名单.xlsx")
    
    class_map = {}
    for class_name in df["班级"].unique():
        cls = Class(name=class_name, grade="高二")
        db.add(cls)
        db.commit()
        db.refresh(cls)
        class_map[class_name] = cls.id
        print(f"创建班级: {class_name} -> ID {cls.id}")
    
    for _, row in df.iterrows():
        student = Student(
            class_id=class_map[row["班级"]],
            student_no=str(row["学号"]),
            name=row["姓名"],
            gender="",
            remark=""
        )
        db.add(student)
    
    db.commit()
    db.close()
    print(f"导入完成，共 {len(df)} 名学生")

if __name__ == "__main__":
    import_roster()

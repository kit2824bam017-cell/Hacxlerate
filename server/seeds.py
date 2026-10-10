import os
import json
from .config import Config
from .database import init_db, get_db
from .models import Board, BoardGrade, Subject, Curriculum, CurriculumUnit, CurriculumUnitTopic, User, TeacherProfile
from .services.auth_service import hash_password

BOARDS = [
    {"name": "Central Board of Secondary Education (CBSE – India)", "slug": "cbse", "grade": "Class 7"},
    {"name": "College Board (US Curriculum / Advanced Placement)", "slug": "college-board", "grade": "Grade 7"},
    {"name": "International Baccalaureate (IB – Global)", "slug": "ib", "grade": "MYP Year 2 (Grade 7)"},
    {"name": "Cambridge Assessment International Education (IGCSE / A-Levels)", "slug": "cambridge", "grade": "Lower Secondary (Stage 8)"},
    {"name": "Pearson Edexcel (UK / International)", "slug": "pearson-edexcel", "grade": "Lower Secondary (Year 8)"},
]

BOARD_FROM_SYLLABUS = {
    "CBSE": "cbse",
    "US Curriculum / College Board": "college-board",
    "International Baccalaureate": "ib",
    "Cambridge (CAIE)": "cambridge",
    "Pearson Edexcel": "pearson-edexcel",
}

def seed_database():
    from flask import Flask
    app = Flask(__name__)
    app.config.from_object(Config)
    init_db(app)
    db = get_db()

    print("Seeding boards and grades...")
    board_objs = {}
    grade_objs = {}
    for b in BOARDS:
        board = db.query(Board).filter_by(slug=b["slug"]).first()
        if not board:
            board = Board(name=b["name"], slug=b["slug"])
            db.add(board)
            db.commit()
        board_objs[b["slug"]] = board

        grade = db.query(BoardGrade).filter_by(board_id=board.id, label=b["grade"]).first()
        if not grade:
            grade = BoardGrade(board_id=board.id, label=b["grade"], canonical_level=7, sort_order=7)
            db.add(grade)
            db.commit()
        grade_objs[board.id] = grade

    # Seed demo accounts
    print("Seeding demo accounts...")
    teacher = db.query(User).filter_by(email="ram.holoroid@gmail.com").first()
    if not teacher:
        teacher = User(
            name="Mr. Ram Sharma",
            email="ram.holoroid@gmail.com",
            password=hash_password("DemoPassword123!"),
            role="teacher",
            otp_verified=True
        )
        db.add(teacher)
        db.commit()
        t_prof = TeacherProfile(
            user_id=teacher.id,
            school_name="Delhi Public School",
            rating=4.9,
            detected_teaching_style="Concept-first",
            onboarding_completed=True,
            grades=["Class 7", "Class 8"],
            subjects=["Science", "Mathematics"],
            teaching_explanation="I teach by linking every scientific theory with everyday phenomena."
        )
        db.add(t_prof)
        db.commit()

    student = db.query(User).filter_by(email="rsamy2426@gmail.com").first()
    if not student:
        cbse_board = board_objs.get("cbse")
        cbse_grade = grade_objs.get(cbse_board.id) if cbse_board else None
        student = User(
            name="Rohan Samy",
            email="rsamy2426@gmail.com",
            password=hash_password("DemoPassword123!"),
            role="student",
            otp_verified=True,
            board_id=cbse_board.id if cbse_board else None,
            grade_id=cbse_grade.id if cbse_grade else None,
            grade="Class 7"
        )
        db.add(student)
        db.commit()

    # Load syllabus from sample_syllabus.json
    base_dir = os.path.abspath(os.path.dirname(__file__))
    syllabus_path = os.path.join(base_dir, "..", "web", "sample_syllabus.json")
    if not os.path.exists(syllabus_path):
        syllabus_path = os.path.join(base_dir, "sample_syllabus.json")

    if os.path.exists(syllabus_path):
        print(f"Loading syllabus from {syllabus_path}...")
        with open(syllabus_path, "r", encoding="utf-8") as f:
            rows = json.load(f)

        for row in rows:
            board_slug = BOARD_FROM_SYLLABUS.get(row.get("board"))
            if not board_slug or board_slug not in board_objs:
                continue
            board = board_objs[board_slug]
            grade = grade_objs.get(board.id)

            subj_label = str(row.get("subject", "Science")).strip()
            if "science" in subj_label.lower():
                subj_label = "Science"
            subj_key = subj_label.lower().replace(" ", "-")

            subject = db.query(Subject).filter_by(key=subj_key).first()
            if not subject:
                subject = Subject(key=subj_key, label=subj_label)
                db.add(subject)
                db.commit()

            curriculum = db.query(Curriculum).filter_by(board_id=board.id, grade_id=grade.id if grade else None, subject_id=subject.id).first()
            if not curriculum:
                curriculum = Curriculum(board_id=board.id, grade_id=grade.id if grade else None, grade=grade.label if grade else "Class 7", subject_id=subject.id)
                db.add(curriculum)
                db.commit()

            unit_title = row.get("unit", "Unit")
            unit = db.query(CurriculumUnit).filter_by(curriculum_id=curriculum.id, title=unit_title).first()
            if not unit:
                unit = CurriculumUnit(curriculum_id=curriculum.id, title=unit_title)
                db.add(unit)
                db.commit()

            topics = row.get("topics", [])
            for t in topics:
                if t and not db.query(CurriculumUnitTopic).filter_by(curriculum_unit_id=unit.id, title=t).first():
                    unit_topic = CurriculumUnitTopic(curriculum_unit_id=unit.id, title=t)
                    db.add(unit_topic)
            db.commit()

    print("Database seeding completed successfully!")

if __name__ == "__main__":
    seed_database()

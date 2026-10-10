import os
import json
from datetime import datetime
from .config import Config
from .database import init_db, get_db
from .models import (
    Board, BoardGrade, Subject, Curriculum, CurriculumUnit, CurriculumUnitTopic,
    User, TeacherProfile, StudentProfile, TeacherRating, Quiz, QuizQuestion,
    StudentLearningRec
)
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

DEMO_TEACHERS = [
    {
        "name": "Mr. Ram Sharma",
        "email": "ram.holoroid@gmail.com",
        "school": "Delhi Public School",
        "rating": 4.9,
        "style": "Concept-first",
        "grades": ["Class 7", "Class 8"],
        "subjects": ["Science", "Mathematics"],
        "bio": "I teach by linking every scientific theory with everyday phenomena and foundational proofs.",
        "avatar": "https://images.unsplash.com/photo-1534528741775-53994a69daeb?w=256&h=256&fit=crop&crop=faces",
    },
    {
        "name": "Dr. Alice Vance",
        "email": "alice.vance@learnai.dev",
        "school": "Cambridge International Academy",
        "rating": 4.95,
        "style": "Socratic",
        "grades": ["Class 7", "Stage 8", "Grade 7"],
        "subjects": ["Science", "Physics"],
        "bio": "I guide students through exploratory questions and thought experiments so they arrive at the answer themselves.",
        "avatar": "https://images.unsplash.com/photo-1573496359142-b8d87734a5a2?w=256&h=256&fit=crop&crop=faces",
    },
    {
        "name": "Prof. Marcus Thorne",
        "email": "marcus.thorne@learnai.dev",
        "school": "St. Jude Collegiate",
        "rating": 4.88,
        "style": "Storytelling",
        "grades": ["Class 7", "Class 8", "MYP Year 2 (Grade 7)"],
        "subjects": ["Mathematics", "Science"],
        "bio": "Every mathematical proof has an exciting historical story and drama behind its discovery.",
        "avatar": "https://images.unsplash.com/photo-1507003211169-0a1dd7228f2d?w=256&h=256&fit=crop&crop=faces",
    },
    {
        "name": "Ms. Priya Patel",
        "email": "priya.patel@learnai.dev",
        "school": "Oakridge International",
        "rating": 4.92,
        "style": "Visual explanation",
        "grades": ["Class 7", "Grade 7"],
        "subjects": ["Science", "Biology"],
        "bio": "I utilize vivid spatial diagrams, mental models, and step-by-step visual breakdowns.",
        "avatar": "https://images.unsplash.com/photo-1580894732486-e7e0081d6367?w=256&h=256&fit=crop&crop=faces",
    },
]

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

    # Seed demo teachers
    print("Seeding demo teachers...")
    teacher_entities = []
    for dt in DEMO_TEACHERS:
        t_user = db.query(User).filter_by(email=dt["email"]).first()
        if not t_user:
            t_user = User(
                name=dt["name"],
                email=dt["email"],
                password=hash_password("DemoPassword123!"),
                role="teacher",
                otp_verified=True
            )
            db.add(t_user)
            db.commit()
            t_prof = TeacherProfile(
                user_id=t_user.id,
                school_name=dt["school"],
                rating=dt["rating"],
                detected_teaching_style=dt["style"],
                onboarding_completed=True,
                grades=dt["grades"],
                subjects=dt["subjects"],
                teaching_explanation=dt["bio"],
                avatar_url=dt["avatar"],
            )
            db.add(t_prof)
            db.commit()
        teacher_entities.append(t_user)

    # Primary demo teacher
    primary_teacher = teacher_entities[0] if teacher_entities else None

    # Seed student demo account
    print("Seeding student demo account...")
    student = db.query(User).filter_by(email="rsamy2426@gmail.com").first()
    cbse_board = board_objs.get("cbse")
    cbse_grade = grade_objs.get(cbse_board.id) if cbse_board else None

    if not student:
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
        s_prof = StudentProfile(
            user_id=student.id,
            board_id=cbse_board.id if cbse_board else None,
            grade_id=cbse_grade.id if cbse_grade else None,
            grade="Class 7"
        )
        db.add(s_prof)
        db.commit()

    # Load syllabus from sample_syllabus.json
    base_dir = os.path.abspath(os.path.dirname(__file__))
    syllabus_path = os.path.join(base_dir, "sample_syllabus.json")
    if not os.path.exists(syllabus_path):
        syllabus_path = os.path.join(base_dir, "..", "sample_syllabus.json")

    sample_science_unit = None
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

            if board_slug == "cbse" and "nutrition" in unit_title.lower():
                sample_science_unit = unit

            topics = row.get("topics", [])
            for t in topics:
                if t and not db.query(CurriculumUnitTopic).filter_by(curriculum_unit_id=unit.id, title=t).first():
                    unit_topic = CurriculumUnitTopic(curriculum_unit_id=unit.id, title=t)
                    db.add(unit_topic)
            db.commit()

    # Seed a published demo quiz
    if primary_teacher and cbse_board and cbse_grade:
        existing_quiz = db.query(Quiz).filter_by(teacher_id=primary_teacher.id, title="Nutrition in Plants & Animals Mastery").first()
        science_subj = db.query(Subject).filter_by(key="science").first()
        if not existing_quiz and science_subj:
            print("Seeding sample quiz...")
            demo_quiz = Quiz(
                teacher_id=primary_teacher.id,
                title="Nutrition in Plants & Animals Mastery",
                board_id=cbse_board.id,
                grade_id=cbse_grade.id,
                grade_label="Class 7",
                subject_id=science_subj.id,
                subject_label="Science",
                curriculum_unit_id=sample_science_unit.id if sample_science_unit else None,
                lesson_title="Nutrition in Plants",
                topic_title="Photosynthesis and Autotrophic Nutrition",
                difficulty="beginner",
                question_count=3,
                status="published",
                published_at=datetime.utcnow()
            )
            db.add(demo_quiz)
            db.commit()

            q1 = QuizQuestion(
                quiz_id=demo_quiz.id,
                sort_order=1,
                type="mcq",
                prompt="Which green pigment in leaves is primarily responsible for capturing solar energy during photosynthesis?",
                options=["Chlorophyll", "Hemoglobin", "Carotene", "Anthocyanin"],
                correct_answer="Chlorophyll",
                explanation="Chlorophyll is the green pigment in the chloroplasts of plant cells that traps sunlight to drive photosynthesis.",
                topic_title="Photosynthesis",
                misconception_hint="Look inside chloroplasts for the green pigment, not plant flower pigments."
            )
            q2 = QuizQuestion(
                quiz_id=demo_quiz.id,
                sort_order=2,
                type="mcq",
                prompt="What are the essential raw materials required by plants to synthesize carbohydrates during photosynthesis?",
                options=[
                    "Carbon dioxide and Water (in presence of Sunlight and Chlorophyll)",
                    "Oxygen and Sugar",
                    "Nitrogen and Soil minerals only",
                    "Hydrogen and Ozone"
                ],
                correct_answer="Carbon dioxide and Water (in presence of Sunlight and Chlorophyll)",
                explanation="Plants take carbon dioxide from the air via stomata and water from soil via roots to produce glucose and oxygen.",
                topic_title="Raw Materials of Photosynthesis",
                misconception_hint="Remember what enters the plant leaves and roots versus what is released."
            )
            q3 = QuizQuestion(
                quiz_id=demo_quiz.id,
                sort_order=3,
                type="mcq",
                prompt="Which tiny pores on the leaf surface regulate gas exchange (carbon dioxide intake and oxygen release)?",
                options=["Stomata", "Chloroplasts", "Xylem vessels", "Phloem tubes"],
                correct_answer="Stomata",
                explanation="Stomata are microscopic pores guarded by guard cells that open and close for transpiration and gas exchange.",
                topic_title="Leaf Structure & Stomata",
                misconception_hint="Think about the aperture/opening mechanism on the leaf's epidermal layer."
            )
            db.add_all([q1, q2, q3])
            db.commit()

    # Seed sample learning recommendation for student
    if student and primary_teacher:
        existing_rec = db.query(StudentLearningRec).filter_by(student_id=student.id).first()
        if not existing_rec:
            print("Seeding sample learning recommendation...")
            rec = StudentLearningRec(
                student_id=student.id,
                teacher_id=primary_teacher.id,
                subject="Science",
                lesson="Nutrition in Plants",
                topic="Photosynthesis and Stomata gas exchange",
                reason="Struggled with gas exchange mechanisms in the last quiz. Review with your teacher in Learn Chat!",
                status="open"
            )
            db.add(rec)
            db.commit()

    print("Database seeding completed successfully with all rich demo teachers, quizzes, and curriculum data!")

if __name__ == "__main__":
    seed_database()

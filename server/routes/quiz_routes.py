import json
import re
from datetime import datetime
from flask import Blueprint, request, jsonify
from ..database import get_db
from ..models import (
    User, Board, BoardGrade, Subject, Curriculum, CurriculumUnit,
    Quiz, QuizQuestion, QuizAttempt, QuizAttemptAnswer, StudentLearningRec
)
from ..services.auth_service import auth_required
from ..services.ai_service import chat_completion

quiz_bp = Blueprint("quiz", __name__)

@quiz_bp.route("/teacher/curriculum", methods=["GET"])
@auth_required(roles="teacher")
def get_curriculum(user):
    db = get_db()
    curricula = db.query(Curriculum).all()
    tree = []
    for c in curricula:
        tree.append({
            "id": c.id,
            "board": c.board.name if c.board else "",
            "board_id": c.board_id,
            "grade": c.board_grade.label if c.board_grade else c.grade,
            "grade_id": c.grade_id,
            "subject": c.subject.label if c.subject else "",
            "subject_id": c.subject_id,
            "units": [u.to_dict() for u in c.units]
        })
    return jsonify({"curriculum": tree})

@quiz_bp.route("/teacher/quizzes", methods=["GET"])
@auth_required(roles="teacher")
def list_teacher_quizzes(user):
    db = get_db()
    quizzes = db.query(Quiz).filter_by(teacher_id=user.id).order_by(Quiz.created_at.desc()).all()
    return jsonify({"quizzes": [q.to_dict() for q in quizzes]})

@quiz_bp.route("/teacher/quizzes", methods=["POST"])
@auth_required(roles="teacher")
def create_teacher_quiz(user):
    db = get_db()
    body = request.get_json() or {}
    title = body.get("title", "Practice Quiz")
    board_id = body.get("board_id")
    grade_id = body.get("grade_id") or 1
    grade_label = body.get("grade_label", "Class 7")
    subject_id = body.get("subject_id")
    subject_label = body.get("subject_label", "Science")
    unit_id = body.get("curriculum_unit_id")
    lesson_title = body.get("lesson_title", "General Topic")
    topic_title = body.get("topic_title")
    difficulty = body.get("difficulty", "beginner")
    question_count = int(body.get("question_count", 5))

    quiz = Quiz(
        teacher_id=user.id,
        title=title,
        board_id=board_id,
        grade_id=grade_id,
        grade_label=grade_label,
        subject_id=subject_id,
        subject_label=subject_label,
        curriculum_unit_id=unit_id,
        lesson_title=lesson_title,
        topic_title=topic_title,
        difficulty=difficulty,
        question_count=question_count,
        status="draft"
    )
    db.add(quiz)
    db.commit()

    return jsonify({"quiz": quiz.to_dict()})

@quiz_bp.route("/teacher/quizzes/<int:quiz_id>", methods=["GET"])
@auth_required(roles="teacher")
def get_teacher_quiz(user, quiz_id):
    db = get_db()
    quiz = db.query(Quiz).filter_by(id=quiz_id, teacher_id=user.id).first()
    if not quiz:
        return jsonify({"message": "Quiz not found."}), 404
    return jsonify({"quiz": quiz.to_dict()})

@quiz_bp.route("/teacher/quizzes/<int:quiz_id>/publish", methods=["POST"])
@auth_required(roles="teacher")
def publish_teacher_quiz(user, quiz_id):
    db = get_db()
    quiz = db.query(Quiz).filter_by(id=quiz_id, teacher_id=user.id).first()
    if not quiz:
        return jsonify({"message": "Quiz not found."}), 404

    quiz.status = "published"
    quiz.published_at = datetime.utcnow()
    quiz.question_count = len(quiz.questions)
    db.commit()

    return jsonify({"message": "Quiz published successfully.", "quiz": quiz.to_dict()})

@quiz_bp.route("/teacher/quizzes/<int:quiz_id>/questions", methods=["POST"])
@auth_required(roles="teacher")
def generate_questions(user, quiz_id):
    db = get_db()
    quiz = db.query(Quiz).filter_by(id=quiz_id, teacher_id=user.id).first()
    if not quiz:
        return jsonify({"message": "Quiz not found."}), 404

    body = request.get_json() or {}
    count = int(body.get("count", quiz.question_count or 5))

    prompt = (
        f"Generate {count} multiple-choice quiz questions for {quiz.grade_label} {quiz.subject_label} "
        f"on '{quiz.lesson_title}' ({quiz.topic_title or 'General'}). Difficulty: {quiz.difficulty}.\n"
        "Return strict JSON array with elements: "
        "{\"type\": \"mcq\", \"prompt\": \"...\", \"options\": [\"A. ...\", \"B. ...\", \"C. ...\", \"D. ...\"], "
        "\"correct_answer\": \"A\", \"explanation\": \"...\", \"misconception_hint\": \"...\"}"
    )

    reply = chat_completion("You are an educational assessment expert. Return JSON array only.", [{"role": "user", "content": prompt}], max_tokens=1500, temperature=0.5)

    created_questions = []
    try:
        match = re.search(r"\[.*\]", reply, re.DOTALL)
        if match:
            items = json.loads(match.group(0))
            for idx, item in enumerate(items):
                q = QuizQuestion(
                    quiz_id=quiz.id,
                    sort_order=len(quiz.questions) + idx + 1,
                    type=item.get("type", "mcq"),
                    prompt=item.get("prompt", "Question"),
                    options=item.get("options", []),
                    correct_answer=str(item.get("correct_answer", "A")),
                    explanation=item.get("explanation", "Standard explanation."),
                    misconception_hint=item.get("misconception_hint", "Check key terms."),
                )
                db.add(q)
                created_questions.append(q)
            db.commit()
    except Exception as e:
        print(f"[QUIZ GEN ERROR] {e}")

    # Fallback if no questions parsed
    if not created_questions:
        q = QuizQuestion(
            quiz_id=quiz.id,
            sort_order=1,
            type="mcq",
            prompt=f"Which fundamental principle governs {quiz.lesson_title}?",
            options=["A. Conservation of Energy", "B. Newton's Third Law", "C. Ohm's Law", "D. Dalton's Atomic Theory"],
            correct_answer="A",
            explanation="The principle is foundational to this syllabus topic.",
            misconception_hint="Look at energy transformations.",
        )
        db.add(q)
        db.commit()
        created_questions.append(q)

    quiz.question_count = len(quiz.questions)
    db.commit()

    return jsonify({"questions": [q.to_dict() for q in created_questions]})

@quiz_bp.route("/teacher/quizzes/<int:quiz_id>/analytics", methods=["GET"])
@auth_required(roles="teacher")
def quiz_analytics(user, quiz_id):
    db = get_db()
    quiz = db.query(Quiz).filter_by(id=quiz_id, teacher_id=user.id).first()
    if not quiz:
        return jsonify({"message": "Quiz not found."}), 404

    attempts = db.query(QuizAttempt).filter_by(quiz_id=quiz.id).all()
    completed = [a for a in attempts if a.status == "completed"]
    scores = [float(a.score_percent) for a in completed if a.score_percent is not None]

    avg_score = round(sum(scores) / len(scores), 1) if scores else 0
    return jsonify({
        "quiz_id": quiz.id,
        "total_attempted": len(attempts),
        "total_completed": len(completed),
        "average_score": avg_score,
        "highest_score": max(scores) if scores else 0,
        "lowest_score": min(scores) if scores else 0,
    })

# --- STUDENT QUIZ ROUTES ---

@quiz_bp.route("/student/quizzes", methods=["GET"])
@auth_required(roles="student")
def list_student_quizzes(user):
    db = get_db()
    quizzes = db.query(Quiz).filter_by(status="published").all()

    attempts_by_quiz = {a.quiz_id: a for a in user.quiz_attempts}

    all_quizzes = []
    available, in_progress, completed = [], [], []
    for q in quizzes:
        att = attempts_by_quiz.get(q.id)
        q_data = q.to_dict()
        if not att:
            q_data["bucket"] = "available"
            available.append(q_data)
        elif att.status == "completed":
            q_data["bucket"] = "completed"
            q_data["attempt"] = att.to_dict()
            completed.append(q_data)
        else:
            q_data["bucket"] = "active"
            q_data["attempt"] = att.to_dict()
            in_progress.append(q_data)
        all_quizzes.append(q_data)

    return jsonify({
        "quizzes": all_quizzes,
        "available": available,
        "in_progress": in_progress,
        "completed": completed,
    })

@quiz_bp.route("/student/quizzes/<int:quiz_id>", methods=["GET"])
@auth_required(roles="student")
def get_student_quiz(user, quiz_id):
    db = get_db()
    quiz = db.query(Quiz).filter_by(id=quiz_id, status="published").first()
    if not quiz:
        return jsonify({"message": "Quiz not found."}), 404

    attempt = db.query(QuizAttempt).filter_by(quiz_id=quiz.id, student_id=user.id).first()
    # Mask answers unless revealed
    questions_data = []
    answers_by_qid = {a.question_id: a for a in attempt.answers} if attempt else {}

    for q in quiz.questions:
        ans = answers_by_qid.get(q.id)
        revealed = bool(ans and (ans.is_correct or ans.incorrect_attempts >= 2))
        q_dict = q.to_dict(include_answer=revealed)
        if ans:
            q_dict["user_answer"] = ans.latest_answer
            q_dict["is_correct"] = ans.is_correct
            q_dict["tutor_thread"] = ans.tutor_thread or []
        questions_data.append(q_dict)

    data = quiz.to_dict()
    data["questions"] = questions_data
    data["attempt"] = attempt.to_dict() if attempt else None
    return jsonify({"quiz": data})

@quiz_bp.route("/student/quizzes/<int:quiz_id>/start", methods=["POST"])
@auth_required(roles="student")
def start_quiz_attempt(user, quiz_id):
    db = get_db()
    quiz = db.query(Quiz).filter_by(id=quiz_id, status="published").first()
    if not quiz:
        return jsonify({"message": "Quiz not found."}), 404

    attempt = db.query(QuizAttempt).filter_by(quiz_id=quiz.id, student_id=user.id).first()
    if not attempt:
        attempt = QuizAttempt(quiz_id=quiz.id, student_id=user.id, status="in_progress")
        db.add(attempt)
        db.commit()

    return jsonify({"message": "Quiz started.", "attempt": attempt.to_dict()})

@quiz_bp.route("/student/quizzes/<int:quiz_id>/answer", methods=["POST"])
@auth_required(roles="student")
def submit_answer(user, quiz_id):
    db = get_db()
    body = request.get_json() or {}
    question_id = body.get("question_id")
    answer_text = str(body.get("answer", "")).strip()

    attempt = db.query(QuizAttempt).filter_by(quiz_id=quiz_id, student_id=user.id).first()
    if not attempt:
        attempt = QuizAttempt(quiz_id=quiz_id, student_id=user.id, status="in_progress")
        db.add(attempt)
        db.commit()

    question = db.query(QuizQuestion).filter_by(id=question_id, quiz_id=quiz_id).first()
    if not question:
        return jsonify({"message": "Question not found."}), 404

    q_ans = db.query(QuizAttemptAnswer).filter_by(attempt_id=attempt.id, question_id=question.id).first()
    if not q_ans:
        q_ans = QuizAttemptAnswer(attempt_id=attempt.id, question_id=question.id, first_answer=answer_text)
        db.add(q_ans)

    # Check correctness (handles "A", "A. ...", etc.)
    norm_expected = question.correct_answer.strip().lower()
    norm_given = answer_text.strip().lower()
    is_correct = (norm_expected == norm_given) or norm_given.startswith(norm_expected)

    if q_ans.first_is_correct is None:
        q_ans.first_is_correct = is_correct

    q_ans.latest_answer = answer_text
    q_ans.is_correct = is_correct

    if not is_correct:
        q_ans.incorrect_attempts += 1
    else:
        q_ans.revealed = True

    if q_ans.incorrect_attempts >= 2:
        q_ans.revealed = True

    # Socratic tutor response
    tutor_reply = ""
    if is_correct:
        tutor_reply = f"Correct! {question.explanation}"
    else:
        tutor_reply = f"Not quite. Hint: {question.misconception_hint or 'Look closely at the question.'}"

    thread = q_ans.tutor_thread or []
    thread.append({"sender": "student", "text": answer_text})
    thread.append({"sender": "tutor", "text": tutor_reply})
    q_ans.tutor_thread = thread

    db.commit()

    # Check if all questions answered to complete attempt
    total_q = len(question.quiz.questions)
    all_ans = db.query(QuizAttemptAnswer).filter_by(attempt_id=attempt.id).all()
    if len(all_ans) >= total_q and all(a.is_correct or a.incorrect_attempts >= 2 for a in all_ans):
        attempt.status = "completed"
        attempt.completed_at = datetime.utcnow()
        correct_count = sum(1 for a in all_ans if a.first_is_correct)
        attempt.correct_count = correct_count
        attempt.score_percent = round((correct_count / total_q) * 100, 2)
        db.commit()

        # Add learning recommendation
        if attempt.score_percent < 80:
            rec = StudentLearningRec(
                student_id=user.id,
                teacher_id=question.quiz.teacher_id,
                quiz_id=question.quiz.id,
                subject=question.quiz.subject_label,
                lesson=question.quiz.lesson_title,
                topic=question.quiz.topic_title or question.quiz.lesson_title,
                reason=f"Scored {attempt.score_percent}% on {question.quiz.title}. Review foundational concepts in Learn chat."
            )
            db.add(rec)
            db.commit()

    return jsonify({
        "is_correct": is_correct,
        "revealed": q_ans.revealed,
        "correct_answer": question.correct_answer if q_ans.revealed else None,
        "explanation": question.explanation if q_ans.revealed else None,
        "tutor_reply": tutor_reply,
        "tutor_thread": q_ans.tutor_thread,
    })

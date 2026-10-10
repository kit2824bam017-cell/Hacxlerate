from flask import Blueprint, request, jsonify
from ..database import get_db
from ..models import User, StudentProfile, Board, BoardGrade, TeacherRating, StudentLearningRec, QuizAttempt, Quiz
from ..services.auth_service import auth_required
from ..services.ai_service import homework_hint_vision

student_bp = Blueprint("student", __name__)

@student_bp.route("/student/dashboard", methods=["GET"])
@auth_required(roles="student")
def student_dashboard(user):
    db = get_db()
    prof = user.student_profile
    board = db.query(Board).filter_by(id=user.board_id).first() if user.board_id else None
    grade = db.query(BoardGrade).filter_by(id=user.grade_id).first() if user.grade_id else None

    # Recommendations
    recs = db.query(StudentLearningRec).filter_by(student_id=user.id).order_by(StudentLearningRec.created_at.desc()).limit(5).all()

    # Recent attempts
    attempts = db.query(QuizAttempt).filter_by(student_id=user.id).order_by(QuizAttempt.created_at.desc()).limit(5).all()

    return jsonify({
        "user": user.to_dict(),
        "board": board.to_dict() if board else None,
        "grade": grade.to_dict() if grade else None,
        "learning_recommendations": [r.to_dict() for r in recs],
        "recent_attempts": [a.to_dict() for a in attempts],
    })

@student_bp.route("/student/session-feedback", methods=["POST"])
@auth_required(roles="student")
def session_feedback(user):
    db = get_db()
    body = request.get_json() or {}
    teacher_id = body.get("teacher_id")
    rating_val = body.get("rating")
    feedback_text = body.get("feedback", "")

    if not teacher_id or not rating_val:
        return jsonify({"message": "teacher_id and rating are required."}), 422

    rating = TeacherRating(
        student_id=user.id,
        teacher_id=int(teacher_id),
        rating=int(rating_val),
        feedback=feedback_text,
    )
    db.add(rating)
    db.commit()

    # Re-calculate teacher average rating
    teacher = db.query(User).filter_by(id=teacher_id).first()
    if teacher and teacher.teacher_profile:
        all_ratings = db.query(TeacherRating).filter_by(teacher_id=teacher.id).all()
        if all_ratings:
            avg = sum(r.rating for r in all_ratings) / len(all_ratings)
            teacher.teacher_profile.rating = round(avg, 2)
            db.commit()

    return jsonify({"message": "Feedback submitted successfully."})

@student_bp.route("/homework-hint", methods=["POST"])
def homework_hint():
    student_prompt = request.form.get("prompt", "")
    image_file = request.files.get("image")
    if not image_file:
        return jsonify({"message": "No image provided."}), 422

    image_bytes = image_file.read()
    mime_type = image_file.mimetype or "image/jpeg"
    hint_text = homework_hint_vision(image_bytes, mime_type, student_prompt)

    return jsonify({"hint": hint_text})

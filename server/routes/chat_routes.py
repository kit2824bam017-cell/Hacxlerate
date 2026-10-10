import io
from flask import Blueprint, request, jsonify, send_file
from ..database import get_db
from ..models import User, LearnTurn
from ..services.auth_service import get_current_user
from ..services.ai_service import chat_completion, build_teacher_system_prompt, build_user_message_with_context
from ..services.speech_service import synthesize_speech, transcribe_audio_bytes

chat_bp = Blueprint("chat", __name__)

@chat_bp.route("/chat", methods=["POST"])
def learn_chat():
    db = get_db()
    body = request.get_json() or {}
    student = get_current_user()

    teacher_id = body.get("teacher_id")
    subject = body.get("subject", "Science")
    lesson = body.get("lesson", "")
    topics = body.get("topics", [])
    question = body.get("question", "")
    history = body.get("history", [])
    difficulty = body.get("difficulty", "beginner")
    response_mode = body.get("response_mode", "text")

    teacher = db.query(User).filter_by(id=teacher_id).first() if teacher_id else None
    teacher_prof = teacher.teacher_profile.to_dict() if teacher and teacher.teacher_profile else {}
    teacher_name = teacher.name if teacher else "Teacher"

    system_prompt = build_teacher_system_prompt(teacher_prof, teacher_name=teacher_name, difficulty=difficulty, response_mode=response_mode)

    context = {
        "grade": student.grade if student else "Class 7",
        "board": student.board.name if student and student.board else "CBSE",
        "subject": subject,
        "lesson": lesson,
        "lessonTopics": topics,
        "difficultyLevel": difficulty,
        "responseMode": response_mode,
    }

    user_msg_content = build_user_message_with_context(question, context)

    # Format history
    messages = []
    for h in history:
        messages.append({
            "role": "user" if h.get("sender") == "student" else "assistant",
            "content": h.get("text", "")
        })
    messages.append({"role": "user", "content": user_msg_content})

    ai_reply = chat_completion(system_prompt, messages, max_tokens=600, temperature=0.6)

    # Log LearnTurn if student is authenticated
    if student and teacher:
        turn = LearnTurn(
            student_id=student.id,
            teacher_id=teacher.id,
            subject=subject,
            lesson=lesson,
            topics=topics,
            question=question,
            answer_preview=ai_reply[:450],
            response_mode=response_mode,
        )
        db.add(turn)
        db.commit()

    return jsonify({
        "reply": ai_reply,
        "teacher": {
            "id": teacher.id if teacher else None,
            "name": teacher_name,
            "voice_id": teacher_prof.get("elevenlabs_voice_id"),
        }
    })

@chat_bp.route("/tts/speak", methods=["POST"])
def tts_speak():
    body = request.get_json() or {}
    text = body.get("text", "")
    voice_name = body.get("voice_name", "en-US-AvaMultilingualNeural")

    if not text:
        return jsonify({"message": "text is required."}), 422

    audio_bytes = synthesize_speech(text, voice_name=voice_name)
    if not audio_bytes:
        return jsonify({"message": "Audio synthesis failed or not configured.", "fallback": True}), 502

    return send_file(
        io.BytesIO(audio_bytes),
        mimetype="audio/mpeg",
        as_attachment=False,
        download_name="speech.mp3"
    )

@chat_bp.route("/speech-to-text", methods=["POST"])
def speech_to_text():
    audio_file = request.files.get("audio")
    lang = request.form.get("language", "en")

    if not audio_file:
        return jsonify({"message": "No audio file provided."}), 422

    transcript = transcribe_audio_bytes(audio_file.read(), language=lang)
    return jsonify({"transcript": transcript})

@chat_bp.route("/chat/video", methods=["POST"])
def chat_video():
    body = request.get_json() or {}
    text = body.get("text", "")
    avatar_url = body.get("avatar_url")

    # Mock / standard D-ID payload
    return jsonify({
        "id": "vid_sample_mock_id",
        "status": "ready",
        "video_url": avatar_url or "",
        "message": "Video talk rendered."
    })

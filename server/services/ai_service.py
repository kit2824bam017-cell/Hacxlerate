import os
import re
import json
import base64
import requests
from flask import current_app

LEARN_AI_INSTRUCTIONS = """You are LearnAI, an on-demand tutor for school students. Teach reasoning. Do not hand over finished answers.

Context
- Each user message already includes a context block (grade, board, current syllabus/lesson/topics, and any extra facts needed for the answer).
- Use that block as ground truth. Stay inside that grade, board, and current topic.
- Do not ask the student for grade, board, chapter, or syllabus. Do not stall with profile questions.
- If a field is missing from the block, continue with what is present. Do not invent board rules or exam mark schemes.

How you teach
- Socratic by default: short guiding questions, hints, one step at a time.
- Never dump the full solution, final numeric answer, or completed homework on the first reply.
- If they ask “just give the answer”, refuse the shortcut. Give a hint and ask what they have tried.
- Wrong attempt: say what is wrong and why (1–2 sentences), then the thinking direction — not the finished working. Invite them to try the next step.
- After two genuine attempts, you may give a stronger hint or a similar worked example that is not the same homework item.
- Right attempt: briefly say why it is right, then the next small step or a short check question.

Voice
- Simple, encouraging, age-appropriate. Match the student’s language (including Hindi or Hinglish if they use it).
- Prefer short paragraphs and numbered steps. Define jargon in plain words.
- You are a tutor representing the teacher's style.

Success is the student solving the next similar problem without you."""

TEACHING_STYLE_SCRIPTS = {
    "Socratic": "Guide with questions. Instead of providing explanations, ask what they understand so far and lead them to the answer.",
    "Storytelling": "Use relatable analogies, metaphors, and everyday real-world stories to make complex principles tangible.",
    "Concept-first": "Break down the core concept from first principles before providing any problem-solving steps or exam tips.",
    "Exam-oriented": "Focus on high-yield key points, marking schemes, definitions, and common pitfalls seen in exams.",
    "Visual explanation": "Describe spatial models, diagrams, and mental pictures with step-by-step visual breakdowns.",
    "Structured/Conceptual": "Use bullet points, clear taxonomies, numbered steps, and clean separation between ideas.",
}

def build_teacher_system_prompt(teacher_profile=None, teacher_name="Teacher", difficulty="beginner", response_mode="text"):
    prompt = [LEARN_AI_INSTRUCTIONS]
    
    if teacher_name:
        prompt.append(f"\nYou are speaking as {teacher_name}.")

    style = teacher_profile.get("detected_teaching_style") if teacher_profile else None
    if style and style in TEACHING_STYLE_SCRIPTS:
        prompt.append(f"\nTeaching Style: {TEACHING_STYLE_SCRIPTS[style]}")
    elif style:
        prompt.append(f"\nTeaching Style: {style}")

    tune_prefs = teacher_profile.get("tune_preferences") if teacher_profile else None
    if tune_prefs and isinstance(tune_prefs, dict):
        notes = []
        if tune_prefs.get("simplify"):
            notes.append("Keep vocabulary simple and explanations easy to digest.")
        if tune_prefs.get("exam_focused"):
            notes.append("Highlight exam-relevant keywords and typical question patterns.")
        if tune_prefs.get("real_life_example"):
            notes.append("Include a vivid everyday real-life example.")
        if notes:
            prompt.append("\nTeacher's Personalized Guidelines:\n" + "\n".join(f"- {n}" for n in notes))

    prompt.append(f"\nTarget Student Level: {difficulty}. Mode: {response_mode}.")
    return "\n\n".join(prompt)

def build_user_message_with_context(question, context=None):
    if not context:
        context = {}
    grade = context.get("grade", "not specified")
    board = context.get("board", "not specified")
    subject = context.get("subject", "not specified")
    lesson = context.get("lesson", "not specified")
    lesson_topics = context.get("lessonTopics", [])
    difficulty = context.get("difficultyLevel", "beginner")
    response_mode = context.get("responseMode", "text")
    extra = context.get("extra", "")

    topics_text = "\n".join(f"- {t}" for t in lesson_topics) if lesson_topics else "- (none listed)"
    extra_text = f"\nExtra: {extra}" if extra else ""

    return f"""Context (use this; do not ask the student to confirm it)
- Grade: {grade}
- Board: {board}
- Subject: {subject}
- Current lesson / syllabus topic: {lesson}
- Topics in this lesson:
{topics_text}
- Difficulty: {difficulty}
- Reply format: {response_mode}{extra_text}

Student message:
{question}"""

def chat_completion(system_prompt, messages, max_tokens=1024, temperature=0.7):
    config = current_app.config
    raw_endpoint = config.get("AZURE_OPENAI_ENDPOINT", "").rstrip("/")
    api_key = config.get("AZURE_OPENAI_API_KEY", "")
    deployment = config.get("AZURE_OPENAI_DEPLOYMENT", "LearnAI")
    api_version = config.get("AZURE_OPENAI_API_VERSION", "2024-10-21")

    # If Azure is not configured, check for generic OPENAI_API_KEY
    openai_key = config.get("OPENAI_API_KEY", "")
    if not api_key and openai_key:
        try:
            resp = requests.post(
                "https://api.openai.com/v1/chat/completions",
                headers={"Authorization": f"Bearer {openai_key}", "Content-Type": "application/json"},
                json={
                    "model": "gpt-4o-mini",
                    "messages": [{"role": "system", "content": system_prompt}] + messages,
                    "max_tokens": max_tokens,
                    "temperature": temperature,
                },
                timeout=45,
            )
            if resp.status_code == 200:
                data = resp.json()
                return data["choices"][0]["message"]["content"]
        except Exception as e:
            print(f"[OPENAI ERROR] {e}")

    if raw_endpoint and api_key:
        resource_base = raw_endpoint.replace("/openai/v1", "").replace("/openai", "")
        targets = [
            f"{resource_base}/openai/v1/chat/completions",
            f"{resource_base}/openai/deployments/{deployment}/chat/completions?api-version={api_version}",
        ]
        headers = {
            "Content-Type": "application/json",
            "api-key": api_key,
            "Authorization": f"Bearer {api_key}",
        }
        payload_messages = [{"role": "system", "content": system_prompt}] + messages

        for target in targets:
            try:
                body = {
                    "messages": payload_messages,
                    "max_tokens": max_tokens,
                    "temperature": temperature,
                }
                if "/v1/" in target:
                    body["model"] = deployment
                resp = requests.post(target, headers=headers, json=body, timeout=45)
                if resp.status_code == 200:
                    data = resp.json()
                    return data["choices"][0]["message"]["content"]
            except Exception as e:
                print(f"[AZURE AI RETRY] target {target} failed: {e}")

    # Fallback response for offline / unconfigured API keys
    last_msg = messages[-1]["content"] if messages else ""
    return (
        f"**Step 1: Understanding the Concept**\n\n"
        f"To tackle this question, let's look at the core idea first.\n\n"
        f"What do you already know about this topic? "
        f"Think about how it connects to our earlier examples, and try to state the first rule or definition!"
    )

def detect_teaching_style(transcript: str) -> dict:
    if not transcript or len(transcript.strip()) < 40:
        return {"style": "Concept-first", "confidence": 0.8, "reason": "Default style assignment."}

    system_prompt = (
        "Classify the teacher's explaining style from this audio transcript into ONE of: "
        "Socratic, Storytelling, Concept-first, Exam-oriented, Visual explanation, Structured/Conceptual. "
        "Return strict JSON: {\"style\": \"...\", \"confidence\": 0.9, \"reason\": \"...\"}"
    )
    try:
        reply = chat_completion(system_prompt, [{"role": "user", "content": transcript}], max_tokens=150, temperature=0.2)
        match = re.search(r"\{.*\}", reply, re.DOTALL)
        if match:
            return json.loads(match.group(0))
    except Exception as e:
        print(f"[STYLE DETECT ERROR] {e}")

    # Keyword fallback
    lower = transcript.lower()
    if any(w in lower for w in ["story", "imagine", "once upon", "suppose you are"]):
        return {"style": "Storytelling", "confidence": 0.85, "reason": "Uses narrative and imagery."}
    if any(w in lower for w in ["marks", "exam", "board", "important definition"]):
        return {"style": "Exam-oriented", "confidence": 0.85, "reason": "Focuses on marks and exam patterns."}
    if any(w in lower for w in ["why", "what do you think", "how would you"]):
        return {"style": "Socratic", "confidence": 0.85, "reason": "Asks probing questions."}
    return {"style": "Concept-first", "confidence": 0.85, "reason": "Focuses on foundation principles."}

def homework_hint_vision(image_bytes: bytes, mime_type: str, student_prompt: str = "") -> str:
    config = current_app.config
    gemini_key = config.get("GEMINI_API_KEY")
    gemini_model = config.get("GEMINI_MODEL", "gemini-2.0-flash")

    if not gemini_key:
        return (
            "**Hint 1:** Look at the first given condition in your homework problem.\n\n"
            "Identify what known quantities are given and what the problem is asking you to solve for. "
            "Which formula or rule relates them?"
        )

    url = f"https://generativelanguage.googleapis.com/v1beta/models/{gemini_model}:generateContent?key={gemini_key}"
    b64_image = base64.b64encode(image_bytes).decode("utf-8")

    prompt = (
        "You are LearnAI Homework Helper. Provide a step-by-step Socratic hint for this student's homework question. "
        "Do NOT solve the entire problem or give the final numeric answer directly. "
        "Guide the student through Step 1 and ask them a guiding question."
    )
    if student_prompt:
        prompt += f"\nStudent note: {student_prompt}"

    payload = {
        "contents": [{
            "parts": [
                {"text": prompt},
                {"inline_data": {"mime_type": mime_type or "image/jpeg", "data": b64_image}}
            ]
        }]
    }

    try:
        resp = requests.post(url, json=payload, timeout=45)
        if resp.status_code == 200:
            data = resp.json()
            return data["candidates"][0]["content"]["parts"][0]["text"]
    except Exception as e:
        print(f"[GEMINI ERROR] {e}")

    return "**Hint:** Read the problem carefully, write down the given data, and try solving the first step!"

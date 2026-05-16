"""
backend/analytics/progress_tracker.py
====================================
Lightweight analytics tracking for the Smart AI Learning Platform.
"""

import os
import json
import logging
from datetime import datetime
from typing import Dict, List, Any

logger = logging.getLogger(__name__)

ANALYTICS_FILE = os.path.join("data", "analytics_data.json")

def _load_data() -> Dict[str, Any]:
    initial_structure = {
        "stats": {
            "total_questions": 0,
            "total_quizzes": 0,
            "average_quiz_score": 0,
            "documents_indexed": 0
        },
        "questions": [],
        "quizzes": [],
        "topic_mastery": {}
    }

    if not os.path.exists(ANALYTICS_FILE):
        os.makedirs(os.path.dirname(ANALYTICS_FILE), exist_ok=True)
        _save_data(initial_structure)
        return initial_structure
    
    try:
        with open(ANALYTICS_FILE, "r") as f:
            data = json.load(f)
            
            # Ensure all expected keys exist
            if not isinstance(data, dict):
                data = initial_structure
            
            if "stats" not in data:
                data["stats"] = initial_structure["stats"]
                data["stats"]["total_questions"] = len(data.get("questions", []))
                data["stats"]["total_quizzes"] = len(data.get("quizzes", []))
            
            for key in ["questions", "quizzes", "topic_mastery"]:
                if key not in data:
                    data[key] = initial_structure[key]
                
            return data
    except (json.JSONDecodeError, IOError):
        return initial_structure

def _save_data(data: Dict[str, Any]):
    with open(ANALYTICS_FILE, "w") as f:
        json.dump(data, f, indent=2)

def record_question(question: str, topic: str, sources: List[str], mode: str):
    data = _load_data()
    data["stats"]["total_questions"] += 1
    
    data["questions"].append({
        "timestamp": datetime.now().isoformat(),
        "question": question,
        "topic": topic,
        "mode": mode
    })
    
    # Update topic frequency
    data["topic_mastery"][topic] = data["topic_mastery"].get(topic, {"questions": 0, "quiz_avg": 0, "quiz_count": 0})
    data["topic_mastery"][topic]["questions"] += 1
    
    _save_data(data)
    logger.info(f"Recorded question about {topic}")

def record_quiz_result(topic: str, score: int, total: int, quiz_type: str):
    data = _load_data()
    data["stats"]["total_quizzes"] += 1
    
    percentage = (score / total) * 100 if total > 0 else 0
    data["quizzes"].append({
        "timestamp": datetime.now().isoformat(),
        "topic": topic,
        "score": score,
        "total": total,
        "percentage": percentage,
        "type": quiz_type
    })
    
    # Update global average
    all_percentages = [q["percentage"] for q in data["quizzes"]]
    data["stats"]["average_quiz_score"] = round(sum(all_percentages) / len(all_percentages), 1)
    
    # Update topic mastery
    topic_data = data["topic_mastery"].get(topic, {"questions": 0, "quiz_avg": 0, "quiz_count": 0})
    current_avg = topic_data["quiz_avg"]
    count = topic_data["quiz_count"]
    new_avg = (current_avg * count + percentage) / (count + 1)
    topic_data["quiz_avg"] = round(new_avg, 1)
    topic_data["quiz_count"] += 1
    data["topic_mastery"][topic] = topic_data
    
    _save_data(data)
    logger.info(f"Recorded quiz result for {topic}: {score}/{total}")

def record_document_indexed(count: int = 1):
    data = _load_data()
    data["stats"]["documents_indexed"] += count
    _save_data(data)

def get_dashboard_data() -> Dict[str, Any]:
    data = _load_data()
    
    # Format for frontend
    topic_summary = []
    for topic, stats in data["topic_mastery"].items():
        mastery = (stats["quiz_avg"] * 0.7 + min(stats["questions"] * 5, 30)) # Mix of quiz and volume
        topic_summary.append({
            "topic": topic,
            "mastery_score": round(min(mastery, 100), 1),
            "question_count": stats["questions"]
        })
    
    recent_activity = []
    # Combine last 5 questions and quizzes
    combined = []
    for q in data["questions"][-5:]:
        combined.append({"type": "question", "timestamp": q["timestamp"], "topic": q["topic"]})
    for q in data["quizzes"][-5:]:
        combined.append({"type": "quiz", "timestamp": q["timestamp"], "topic": q["topic"]})
    
    combined.sort(key=lambda x: x["timestamp"], reverse=True)
    recent_activity = combined[:5]
    
    return {
        "stats": data["stats"],
        "topic_summary": topic_summary,
        "recent_activity": recent_activity
    }

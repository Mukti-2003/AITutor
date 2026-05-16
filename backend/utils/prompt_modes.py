"""
backend/utils/prompt_modes.py
============================
Specialized prompt templates for different explanation modes and languages.
"""

from langchain_core.prompts import ChatPromptTemplate

MODES = {
    "beginner": {
        "description": "Simple language, analogies, and basic concepts.",
        "instructions": "Use simple language, real-world analogies, and avoid technical jargon. Explain as if to a 10-year-old."
    },
    "exam": {
        "description": "Structured, concise, and focused on key points for university exams.",
        "instructions": "Provide a structured, academic answer suitable for a university-level exam (5-10 marks). Use headings, bullet points, and highlight key terms."
    },
    "technical": {
        "description": "In-depth analysis with advanced terminology and formulas.",
        "instructions": "Provide a deep technical explanation. Include architectural details, advanced terminology, and LaTeX formulas where applicable."
    }
}

BILINGUAL_INSTRUCTIONS = {
    "hindi": "Please provide the answer in Hindi. Ensure the technical terms are preserved in English in parentheses if necessary. Ground the answer strictly in the provided context.",
    "english": "Please provide the answer in English. Ground the answer strictly in the provided context."
}

def get_mode_prompt(mode: str, context: str, question: str, language: str = "english") -> str:
    """
    Construct a prompt based on the selected mode and language.
    """
    mode_info = MODES.get(mode.lower(), MODES["beginner"])
    lang_instruction = BILINGUAL_INSTRUCTIONS.get(language.lower(), BILINGUAL_INSTRUCTIONS["english"])
    
    template = f"""
You are an expert Educational Assistant.
{mode_info['instructions']}
{lang_instruction}

Context:
{{context}}

---

Question: {{question}}
Answer:
"""
    return ChatPromptTemplate.from_template(template).format(
        context=context,
        question=question
    )

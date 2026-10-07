from __future__ import annotations

import re


_PRIVATE_QUESTION = re.compile(
    r"\b(race|ethnicity|gender identity|sexual orientation|religion|disability|"
    r"veteran status|date of birth|birth date|age|criminal history|medical condition)\b",
    re.IGNORECASE,
)
_STOP_WORDS = {
    "about", "and", "are", "describe", "experience", "for", "from", "have", "how",
    "into", "please", "provide", "relevant", "tell", "that", "the", "this", "what",
    "when", "where", "which", "with", "would", "your",
}


def is_private_question(question: str) -> bool:
    return bool(_PRIVATE_QUESTION.search(question))


def find_resume_answer(question: str, resume_text: str) -> str | None:
    if not question or not resume_text or is_private_question(question):
        return None

    terms = {
        term for term in re.findall(r"[a-z0-9+#.-]+", question.casefold())
        if len(term) > 2 and term not in _STOP_WORDS
    }
    if not terms:
        return None

    sentences = [
        re.sub(r"\s+", " ", sentence).strip()
        for sentence in re.split(r"(?<=[.!?])\s+|\n+", resume_text)
    ]
    best_sentence: str | None = None
    best_score = 0.0
    best_overlap = 0
    for sentence in sentences:
        if not sentence:
            continue
        sentence_terms = set(re.findall(r"[a-z0-9+#.-]+", sentence.casefold()))
        overlap = len(terms & sentence_terms)
        if overlap == 0:
            continue
        score = overlap / len(terms)
        if (overlap, score) > (best_overlap, best_score):
            best_sentence = sentence
            best_overlap = overlap
            best_score = score

    if best_sentence is None or best_overlap == 0:
        return None
    if best_overlap < 2 and not any(len(term) >= 5 for term in terms & set(best_sentence.casefold().split())):
        return None
    return best_sentence[:600]

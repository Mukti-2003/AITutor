import re


def _tokenize(text):
    return re.findall(r"\w+", text.lower())


def calculate_metrics(prediction, reference):
    """
    Compute token-overlap precision, recall, and F1.
    Returns percentage strings for Streamlit metric display.
    """
    pred_tokens = _tokenize(prediction)
    ref_tokens = _tokenize(reference)

    if not pred_tokens and not ref_tokens:
        precision = recall = f1_score = 1.0
    elif not pred_tokens or not ref_tokens:
        precision = recall = f1_score = 0.0
    else:
        pred_set = set(pred_tokens)
        ref_set = set(ref_tokens)
        overlap = len(pred_set & ref_set)

        precision = overlap / len(pred_set) if pred_set else 0.0
        recall = overlap / len(ref_set) if ref_set else 0.0
        if precision + recall == 0:
            f1_score = 0.0
        else:
            f1_score = 2 * precision * recall / (precision + recall)

    return {
        "Precision": f"{precision * 100:.2f}%",
        "Recall": f"{recall * 100:.2f}%",
        "F1 Score": f"{f1_score * 100:.2f}%",
    }

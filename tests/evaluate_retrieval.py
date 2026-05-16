import json
import os
import sys
import math
from dotenv import load_dotenv
load_dotenv()

sys.path.append(os.path.join(os.path.dirname(__file__), '..'))

from langchain_chroma import Chroma
from backend.llm_manager import get_embedding_function

CHROMA_PATH = "chroma"
K = 5

DATASET_PATH = os.path.join(os.path.dirname(__file__), "eval_dataset.json")


def text_contains_keywords(text, keywords):
    text = text.lower()
    return any(kw.lower() in text for kw in keywords)


def precision_at_k(results, relevant_keywords, k):
    relevant = 0

    for doc in results[:k]:
        if text_contains_keywords(doc.page_content, relevant_keywords):
            relevant += 1

    return relevant / k


def recall_at_k(results, relevant_keywords):

    unique_hits = set()

    for doc in results:
        text = doc.page_content.lower()

        for kw in relevant_keywords:
            if kw.lower() in text:
                unique_hits.add(kw.lower())

    return len(unique_hits) / len(relevant_keywords)


def dcg(relevances):
    score = 0

    for i, rel in enumerate(relevances):
        score += rel / math.log2(i + 2)

    return score


def ndcg_at_k(results, relevant_keywords, k):
    relevances = []

    for doc in results[:k]:
        if text_contains_keywords(doc.page_content, relevant_keywords):
            relevances.append(1)
        else:
            relevances.append(0)

    ideal = sorted(relevances, reverse=True)

    actual_dcg = dcg(relevances)
    ideal_dcg = dcg(ideal)

    if ideal_dcg == 0:
        return 0

    return actual_dcg / ideal_dcg


def evaluate():
    with open(DATASET_PATH, encoding="utf-8") as f:
        dataset = json.load(f)

    db = Chroma(
        persist_directory=CHROMA_PATH,
        embedding_function=get_embedding_function()
    )

    precision_scores = []
    recall_scores = []
    mrr_scores = []
    ndcg_scores = []
    hit_scores = []

    for sample in dataset:
        question = sample["question"]
        relevant_keywords = sample["relevant_keywords"]

        results = db.similarity_search(question, k=K)

        hit = 0
        reciprocal_rank = 0

        for i, doc in enumerate(results):
            if text_contains_keywords(doc.page_content, relevant_keywords):
                hit = 1
                reciprocal_rank = 1 / (i + 1)
                break

        precision = precision_at_k(results, relevant_keywords, K)
        recall = recall_at_k(results, relevant_keywords)
        ndcg = ndcg_at_k(results, relevant_keywords, K)

        precision_scores.append(precision)
        recall_scores.append(recall)
        mrr_scores.append(reciprocal_rank)
        ndcg_scores.append(ndcg)
        hit_scores.append(hit)

        print("\n===================================")
        print(f"Question: {question}")
        print(f"Hit@{K}: {hit}")
        print(f"Precision@{K}: {precision:.2f}")
        print(f"Recall@{K}: {recall:.2f}")
        print(f"MRR: {reciprocal_rank:.2f}")
        print(f"NDCG@{K}: {ndcg:.2f}")

    print("\n========== FINAL RETRIEVAL SCORES ==========")
    print(f"Average Hit@{K}: {sum(hit_scores)/len(hit_scores):.2f}")
    print(f"Average Precision@{K}: {sum(precision_scores)/len(precision_scores):.2f}")
    print(f"Average Recall@{K}: {sum(recall_scores)/len(recall_scores):.2f}")
    print(f"Average MRR: {sum(mrr_scores)/len(mrr_scores):.2f}")
    print(f"Average NDCG@{K}: {sum(ndcg_scores)/len(ndcg_scores):.2f}")


if __name__ == "__main__":
    evaluate()
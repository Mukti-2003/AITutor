import json
import os
import sys
import time
from dotenv import load_dotenv
load_dotenv()

from nltk.translate.bleu_score import sentence_bleu
from rouge_score import rouge_scorer
from bert_score import score as bertscore

sys.path.append(os.path.join(os.path.dirname(__file__), '..'))

from scripts.query_data import query_rag

DATASET_PATH = os.path.join(os.path.dirname(__file__), "eval_dataset.json")


def exact_match(prediction, reference):
    return int(prediction.strip().lower() == reference.strip().lower())


def keyword_score(answer_text, keywords):
    answer_text = answer_text.lower()
    hits = sum(1 for kw in keywords if kw.lower() in answer_text)
    return hits / len(keywords)


def evaluate():
    with open(DATASET_PATH, encoding="utf-8") as f:
        dataset = json.load(f)

    bleu_scores = []
    rouge_scores = []
    bert_scores = []
    em_scores = []
    latency_scores = []
    relevance_scores = []

    scorer = rouge_scorer.RougeScorer(['rouge1'], use_stemmer=True)

    for sample in dataset:
        question = sample["question"]

        expected_keywords = sample["expected_keywords"]

        reference_answer = " ".join(expected_keywords)

        start = time.time()

        generated_answer = query_rag(question)

        end = time.time()

        latency = end - start

        bleu = sentence_bleu(
            [reference_answer.split()],
            generated_answer.split()
        )

        rouge = scorer.score(reference_answer, generated_answer)

        P, R, F1 = bertscore(
            [generated_answer],
            [reference_answer],
            lang="en"
        )

        em = exact_match(generated_answer, reference_answer)

        relevance = keyword_score(generated_answer, expected_keywords)

        bleu_scores.append(bleu)
        rouge_scores.append(rouge['rouge1'].fmeasure)
        bert_scores.append(F1.mean().item())
        em_scores.append(em)
        latency_scores.append(latency)
        relevance_scores.append(relevance)

        print("\n====================================")
        print(f"Question: {question}")
        print(f"BLEU: {bleu:.2f}")
        print(f"ROUGE-1: {rouge['rouge1'].fmeasure:.2f}")
        print(f"BERTScore: {F1.mean().item():.2f}")
        print(f"Exact Match: {em}")
        print(f"Answer Relevancy: {relevance:.2f}")
        print(f"Latency: {latency:.2f} sec")

    print("\n========== FINAL GENERATION SCORES ==========")
    print(f"Average BLEU: {sum(bleu_scores)/len(bleu_scores):.2f}")
    print(f"Average ROUGE-1: {sum(rouge_scores)/len(rouge_scores):.2f}")
    print(f"Average BERTScore: {sum(bert_scores)/len(bert_scores):.2f}")
    print(f"Average Exact Match: {sum(em_scores)/len(em_scores):.2f}")
    print(f"Average Relevancy: {sum(relevance_scores)/len(relevance_scores):.2f}")
    print(f"Average Latency: {sum(latency_scores)/len(latency_scores):.2f} sec")


if __name__ == "__main__":
    evaluate()
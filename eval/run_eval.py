import json
import sys
import os
from pathlib import Path
from typing import Dict, Any, List

from pydantic import BaseModel, Field
from langchain_core.prompts import ChatPromptTemplate

from app.core.database import SessionLocal
from app.models.user import User
from app.agent.graph import run_agent_graph
from app.baseline.dumb_baseline import answer_question_baseline
from app.llm.llm_setup import get_llm

class AnswerAssessment(BaseModel):
    assessment: str = Field(description="Brief explanation of whether the answer meets the expected criteria")
    passes: bool = Field(description="True if the answer successfully meets all expected criteria")

class EvaluationResult(BaseModel):
    agent: AnswerAssessment
    baseline: AnswerAssessment

def evaluate_answers(question: str, criteria: str, agent_answer: str, baseline_answer: str) -> EvaluationResult:
    """Uses LLM to perform a first-pass structured assessment of both answers."""
    llm = get_llm().with_structured_output(EvaluationResult)
    
    prompt = ChatPromptTemplate.from_messages([
        ("system", "You are an impartial evaluator grading AI responses against a strict rubric. Your job is to determine if the answers meet the expected criteria."),
        ("human", "Question: {question}\n\nExpected Criteria:\n{criteria}\n\nAgent Answer:\n{agent_answer}\n\nBaseline Answer:\n{baseline_answer}\n\nEvaluate both answers based STRICTLY on the expected criteria.")
    ])
    
    chain = prompt | llm
    return chain.invoke({
        "question": question,
        "criteria": criteria,
        "agent_answer": agent_answer,
        "baseline_answer": baseline_answer
    })

def main():
    db = SessionLocal()
    # Find the user that has the real data (one@gmail.com based on previous checks)
    user = db.query(User).filter(User.email == "one@gmail.com").first()
    if not user:
        # Fallback to just the first user
        user = db.query(User).first()
        
    if not user:
        print("Error: No user found in database.")
        sys.exit(1)
        
    user_id = user.id
    questions_path = Path(__file__).resolve().parent / "eval_questions.json"
    results_path = Path(__file__).resolve().parent / "eval_results.json"
    
    if not questions_path.exists():
        print(f"Error: Could not find question file at {questions_path}")
        sys.exit(1)
        
    try:
        with open(questions_path, "r") as f:
            questions = json.load(f)
    except json.JSONDecodeError:
        print(f"Error: {questions_path} is not valid JSON.")
        sys.exit(1)
        
    if not isinstance(questions, list):
        print("Error: Questions file must contain a list of objects.")
        sys.exit(1)
        
    results = []
    
    print(f"Running evaluation against {len(questions)} questions...")
    print("=" * 80)
    
    for idx, q in enumerate(questions):
        qid = q.get("id", f"Q{idx+1}")
        q_text = q.get("question", "")
        q_type = q.get("question_type", "Unknown")
        criteria = q.get("expected_answer_criteria", "")
        
        print(f"[{qid}] Type: {q_type}")
        print(f"Q: {q_text}")
        print("Running Agent...")
        try:
            agent_res = run_agent_graph(user_id=user_id, question=q_text)
            agent_answer = agent_res.get("answer", "")
        except Exception as e:
            agent_answer = f"ERROR: {str(e)}"
            
        print("Running Baseline...")
        try:
            baseline_res = answer_question_baseline(user_id=user_id, question=q_text)
            baseline_answer = baseline_res.get("answer", "")
        except Exception as e:
            baseline_answer = f"ERROR: {str(e)}"
            
        print("Running First-Pass Assessment...")
        try:
            assessment = evaluate_answers(q_text, criteria, agent_answer, baseline_answer)
        except Exception as e:
            print(f"Failed to run LLM assessment: {e}")
            assessment = EvaluationResult(
                agent=AnswerAssessment(assessment="Eval failed", passes=False),
                baseline=AnswerAssessment(assessment="Eval failed", passes=False)
            )
            
        result_entry = {
            "id": qid,
            "question": q_text,
            "type": q_type,
            "criteria": criteria,
            "agent_output": {
                "answer": agent_answer,
                "llm_assessment": assessment.agent.assessment,
                "llm_pass": assessment.agent.passes
            },
            "baseline_output": {
                "answer": baseline_answer,
                "llm_assessment": assessment.baseline.assessment,
                "llm_pass": assessment.baseline.passes
            },
            # Manual override fields (to be filled by human)
            "manual_agent_pass": None,
            "manual_baseline_pass": None,
            "manual_notes": ""
        }
        results.append(result_entry)
        print("-" * 80)
        
    with open(results_path, "w") as f:
        json.dump(results, f, indent=2)
        
    print(f"\nSaved results to {results_path}")
    print("\n" + "=" * 40 + " SUMMARY " + "=" * 40)
    print(f"{'Type':<35} | {'Agent Pass':<12} | {'Baseline Pass'}")
    print("-" * 80)
    
    type_stats = {}
    for r in results:
        t = r["type"]
        if t not in type_stats:
            type_stats[t] = {"agent": 0, "baseline": 0, "total": 0}
        type_stats[t]["total"] += 1
        if r["agent_output"]["llm_pass"]:
            type_stats[t]["agent"] += 1
        if r["baseline_output"]["llm_pass"]:
            type_stats[t]["baseline"] += 1
            
    total_agent = 0
    total_baseline = 0
    for t, stats in type_stats.items():
        print(f"{t[:33]:<35} | {stats['agent']}/{stats['total']:<10} | {stats['baseline']}/{stats['total']}")
        total_agent += stats['agent']
        total_baseline += stats['baseline']
        
    print("-" * 80)
    print(f"{'TOTAL (LLM FIRST-PASS)':<35} | {total_agent}/{len(results):<10} | {total_baseline}/{len(results)}")
    print("=" * 87)
    print("NOTE: The above scores are LLM first-pass self-grades. Please review eval_results.json")
    print("and fill in 'manual_agent_pass' / 'manual_baseline_pass' for final scoring.")

if __name__ == "__main__":
    main()

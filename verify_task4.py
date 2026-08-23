import os
import json
from app.agent.nodes import conflict_checker_node
from app.agent.state import AgentState

def print_result(desc, state):
    print(f"\n=== {desc} ===")
    print(f"Check Status: {state['check_status']}")
    print(f"Conflicts Detected: {json.dumps(state['conflicts_detected'], indent=2)}")
    print("="*40)

def verify_live():
    # 1. Planted contradiction
    state1 = AgentState(
        user_id="test", question="", sub_goals=[], tool_calls=[], final_answer=None,
        retrieved_chunks=[
            {"text": "I interviewed the candidate. We should definitely extend an offer.", "metadata": {"sender": "alice@company.com", "subject": "Interview Feedback", "sent_at": "2026-08-01"}},
            {"text": "I interviewed the candidate. We should reject them immediately.", "metadata": {"sender": "bob@company.com", "subject": "Interview Feedback", "sent_at": "2026-08-01"}},
        ],
        conflicts_detected=[],
        check_status=""
    )
    res1 = conflict_checker_node(state1)
    print_result("TEST 1: Planted Contradiction", res1)

    # 2. No contradiction
    state2 = AgentState(
        user_id="test", question="", sub_goals=[], tool_calls=[], final_answer=None,
        retrieved_chunks=[
            {"text": "We received your application for the Software Engineer role.", "metadata": {"sender": "careers@company.com", "subject": "App Received", "sent_at": "2026-08-01"}},
            {"text": "Your resume is under review by the hiring manager.", "metadata": {"sender": "recruiter@company.com", "subject": "Update", "sent_at": "2026-08-02"}},
        ],
        conflicts_detected=[],
        check_status=""
    )
    res2 = conflict_checker_node(state2)
    print_result("TEST 2: No Contradiction", res2)

    # 3. Simulated API Failure
    import app.agent.nodes
    original_get_llm = app.agent.nodes.get_llm
    
    def fake_get_llm(temperature):
        # Return a model with a fake provider/URL that will fail
        from langchain_openai import ChatOpenAI
        return ChatOpenAI(model="stealth/ox-alpha", api_key="fake", base_url="http://localhost:9999/does-not-exist", max_retries=0)
        
    app.agent.nodes.get_llm = fake_get_llm
    
    state3 = AgentState(
        user_id="test", question="", sub_goals=[], tool_calls=[], final_answer=None,
        retrieved_chunks=[{"text": "Some text", "metadata": {}}],
        conflicts_detected=[],
        check_status=""
    )
    res3 = conflict_checker_node(state3)
    print_result("TEST 3: Simulated API Failure", res3)
    
    app.agent.nodes.get_llm = original_get_llm

if __name__ == "__main__":
    verify_live()

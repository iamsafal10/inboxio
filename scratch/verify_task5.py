import os
import json
from app.agent.graph import app_graph
from app.agent.state import AgentState

# Mock the retriever to return specific chunks based on the query,
# since the real retriever node is still a stub in the codebase.
def mock_retriever_node(state: AgentState) -> AgentState:
    question = state.get("question", "").lower()
    
    if "contradiction" in question or "interview" in question:
        # Provide a contradiction
        chunks = [
            {"text": "The candidate's final interview is scheduled for Monday at 10 AM.", "metadata": {"sender": "recruiter@company.com", "subject": "Interview", "sent_at": "2026-08-01"}},
            {"text": "Just confirming the final interview is on Tuesday at 2 PM.", "metadata": {"sender": "coordinator@company.com", "subject": "Interview", "sent_at": "2026-08-01"}}
        ]
    elif "thin" in question or "lunch" in question:
        # Provide thin/unrelated evidence
        chunks = [
            {"text": "Don't forget to submit your timesheets by Friday.", "metadata": {"sender": "hr@company.com", "subject": "Reminder", "sent_at": "2026-08-05"}}
        ]
    else:
        # Normal case
        chunks = [
            {"text": "The project deadline has been extended to November 15th.", "metadata": {"sender": "manager@company.com", "subject": "Project Update", "sent_at": "2026-08-10"}},
            {"text": "Please ensure all code is merged by November 10th for QA.", "metadata": {"sender": "lead@company.com", "subject": "Code Freeze", "sent_at": "2026-08-11"}}
        ]
        
    return {**state, "retrieved_chunks": chunks}

def verify_live():
    # Patch the graph's retriever node for this test
    # Wait, the graph is compiled. We can't patch nodes easily after compilation.
    # Instead, let's just run the graph, but before running, we can monkey-patch the original function.
    import app.agent.nodes
    original_retriever = app.agent.nodes.retriever_node
    app.agent.nodes.retriever_node = mock_retriever_node
    
    # Actually, if the graph was compiled with the old function reference, monkey-patching the module might not work.
    # We must patch it in the graph object or recompile. Let's recompile for safety.
    from app.agent.graph import build_graph
    patched_graph = build_graph()
    
    import time
    from app.agent.nodes import synthesizer_node
    
    questions = [
        ("Normal Case", "When is the project deadline and code freeze?")
    ]
    
    print("\n" + "="*50)
    print("RUNNING TASK 5 VERIFICATION (DIRECT SYNTHESIZER - OX ALPHA)")
    print("="*50)
    
    for desc, q in questions:
        print(f"\n>>> {desc}")
        print(f"Question: {q}")
        
        initial_status = "passed"
        
        initial_state = AgentState(
            user_id="test", question=q, sub_goals=[], tool_calls=[], retrieved_chunks=[], conflicts_detected=[], check_status=initial_status, final_answer=None, citations=[]
        )
        
        # Mocking retriever explicitly for the state
        initial_state = mock_retriever_node(initial_state)
        
        final_state = synthesizer_node(initial_state)
        
        print("\n--- Final Answer ---")
        print(final_state.get("final_answer"))
        print("\n--- Citations ---")
        print(json.dumps(final_state.get("citations"), indent=2))
        print("-" * 50)
        
    app.agent.nodes.retriever_node = original_retriever

if __name__ == "__main__":
    verify_live()

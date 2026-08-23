import json
import pytest
import sys
from pathlib import Path
from unittest.mock import patch, MagicMock

from eval.run_eval import main, evaluate_answers, EvaluationResult, AnswerAssessment

@pytest.fixture
def mock_db():
    with patch("eval.run_eval.SessionLocal") as mock_session:
        mock_db_instance = MagicMock()
        mock_session.return_value = mock_db_instance
        
        mock_user = MagicMock()
        mock_user.id = "test-user-id"
        mock_db_instance.query.return_value.first.return_value = mock_user
        
        yield mock_session

@pytest.fixture
def mock_paths(tmp_path):
    questions_path = tmp_path / "eval_questions.json"
    results_path = tmp_path / "eval_results.json"
    
    with patch("eval.run_eval.Path") as mock_path:
        mock_path_instance = MagicMock()
        mock_path.return_value = mock_path_instance
        mock_path_instance.resolve.return_value.parent.__truediv__.side_effect = lambda x: questions_path if x == "eval_questions.json" else results_path
        
        yield questions_path, results_path

def test_missing_file_exits(mock_db, mock_paths):
    questions_path, _ = mock_paths
    # Don't create the file
    with patch.object(sys, "exit", side_effect=SystemExit) as mock_exit, patch("builtins.print") as mock_print:
        with pytest.raises(SystemExit):
            main()
        mock_exit.assert_called_once_with(1)
        mock_print.assert_called_with(f"Error: Could not find question file at {questions_path}")

def test_malformed_json_exits(mock_db, mock_paths):
    questions_path, _ = mock_paths
    questions_path.write_text("invalid json")
    with patch.object(sys, "exit", side_effect=SystemExit) as mock_exit:
        with pytest.raises(SystemExit):
            main()
        mock_exit.assert_called_once_with(1)

def test_successful_evaluation(mock_db, mock_paths):
    questions_path, results_path = mock_paths
    
    # Create valid mock questions
    questions = [
        {
            "id": "Q1",
            "question": "Test question?",
            "question_type": "Lookup",
            "expected_answer_criteria": "Must say test"
        }
    ]
    questions_path.write_text(json.dumps(questions))
    
    with patch("eval.run_eval.run_agent_graph") as mock_agent, \
         patch("eval.run_eval.answer_question_baseline") as mock_baseline, \
         patch("eval.run_eval.evaluate_answers") as mock_evaluator:
             
        mock_agent.return_value = {"final_answer": "Agent answer"}
        mock_baseline.return_value = {"answer": "Baseline answer"}
        
        mock_evaluator.return_value = EvaluationResult(
            agent=AnswerAssessment(assessment="Good", passes=True),
            baseline=AnswerAssessment(assessment="Bad", passes=False)
        )
        
        main()
        
        # Assert calls
        mock_agent.assert_called_once()
        mock_baseline.assert_called_once()
        mock_evaluator.assert_called_once_with("Test question?", "Must say test", "Agent answer", "Baseline answer")
        
        # Check output file
        assert results_path.exists()
        results = json.loads(results_path.read_text())
        
        assert len(results) == 1
        res = results[0]
        assert res["id"] == "Q1"
        assert res["agent_output"]["answer"] == "Agent answer"
        assert res["agent_output"]["llm_pass"] is True
        assert res["baseline_output"]["answer"] == "Baseline answer"
        assert res["baseline_output"]["llm_pass"] is False
        
        # Check manual overrides are present
        assert "manual_agent_pass" in res
        assert "manual_baseline_pass" in res
        assert "manual_notes" in res

import pytest
from app.services.domain_filter import is_career_related, is_career_question

def test_is_career_related_true():
    assert is_career_related("Job Application Status", "recruiter@tech.com", "We would like to interview you.") == True
    assert is_career_related("Next steps", "hr@company.com", "Here is your offer letter.") == True
    assert is_career_related("Internship update", "university@school.edu", "Please submit your resume.") == True

def test_is_career_related_false():
    assert is_career_related("Your Amazon Order", "auto-confirm@amazon.com", "Your package has shipped.") == False
    assert is_career_related("Flight details", "booking@airline.com", "Your flight to NY is confirmed.") == False
    assert is_career_related("Dinner tonight?", "friend@email.com", "Are we still on for dinner?") == False

def test_is_career_question_true():
    assert is_career_question("Did I get any interview invites today?") == True
    assert is_career_question("What is the status of my internship application?") == True
    assert is_career_question("Show me emails from recruiters.") == True

def test_is_career_question_false():
    assert is_career_question("When is my flight to Boston?") == False
    assert is_career_question("Did my mom send me a recipe?") == False
    assert is_career_question("What did I order on Amazon last week?") == False

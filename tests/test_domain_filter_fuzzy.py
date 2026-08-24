import pytest
from app.services.domain_filter import is_career_question, is_career_related

def test_domain_filter_fuzzy():
    # Exact matches
    assert is_career_question("job opportunity") == True
    assert is_career_question("intern") == True
    assert is_career_question("software engineering role") == True
    
    # Typos (fuzzy matches)
    assert is_career_question("any inetrn opeing mail in") == True
    assert is_career_question("job oppurtunity at honeywell") == True
    
    # Non-career
    assert is_career_question("what is for dinner") == False
    assert is_career_question("random conversation") == False

def test_domain_filter_email_fuzzy():
    assert is_career_related("Re: your inetrnship", "recruiter@tech.com", "We would like to offer...") == True
    assert is_career_related("Lunch?", "friend@gmail.com", "Hey, want to grab lunch?") == False

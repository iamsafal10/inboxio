import sys
from app.services.critique import self_critique

def main():
    print("Testing clean draft...")
    clean_draft = "I have an 8.4 GPA."
    clean_chunks = ["My GPA is 8.4"]
    
    clean_flags = self_critique(clean_draft, clean_chunks)
    print("Clean flags:", clean_flags)
    
    print("\nTesting flagged draft...")
    flagged_draft = "I have an 8.4 GPA, and I'm a certified AWS Solutions Architect with 10 years of experience."
    
    flagged_flags = self_critique(flagged_draft, clean_chunks)
    print("Flagged claims:")
    for flag in flagged_flags:
        print(f"- CLAIM: {flag['claim']}\n  TRUTH: {flag['truth']}")

if __name__ == "__main__":
    main()

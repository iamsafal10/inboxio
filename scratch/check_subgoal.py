from app.core.database import SessionLocal
from app.models.user import User
from app.services.semantic_search import search_emails

db = SessionLocal()
user = db.query(User).filter_by(email="one@gmail.com").first()

sg1 = "Locate the email from MCube AI about the Backend Development internship and record its arrival date/time."
sg2 = "Search the mailbox for any email(s) from Internshala referencing 'Web Development' internships."

for sg in [sg1, sg2]:
    print(f"\n--- Query: {sg}")
    res = search_emails(user.id, sg)
    for i, r in enumerate(res):
        print(f"Rank {i+1} | Distance: {r['distance']:.4f} | Subj: {r['metadata']['subject']}")

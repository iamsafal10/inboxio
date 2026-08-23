from app.core.database import SessionLocal
from app.models.user import User
from app.models.email_indexed import EmailIndexed
from sqlalchemy import func

db = SessionLocal()
users = db.query(User).all()
found_any = False

for user in users:
    total_emails = db.query(EmailIndexed).filter(EmailIndexed.user_id == user.id).count()
    if total_emails > 0:
        found_any = True
        relevant_emails = db.query(EmailIndexed).filter(
            EmailIndexed.user_id == user.id,
            (EmailIndexed.subject.ilike('%job%') | EmailIndexed.subject.ilike('%internship%') | 
             EmailIndexed.body.ilike('%job%') | EmailIndexed.body.ilike('%internship%'))
        ).count()
        
        print(f"User: {user.email}")
        print(f"Total emails indexed: {total_emails}")
        print(f"Relevant emails (job/internship): {relevant_emails}")

if not found_any:
    print("NO EMAILS INDEXED FOR ANY USER in the database.")

db.close()

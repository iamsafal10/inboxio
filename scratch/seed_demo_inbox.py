"""Seed a demo user with synthetic career emails, profile, and embeddings.

Debug/demo tooling — not product code. Lets the full RAG + cold-email path be
exercised end-to-end without connecting a real Gmail account.

Usage:
    python scratch/seed_demo_inbox.py [email] [password]
"""

import sys
import uuid
from datetime import datetime, timedelta, timezone

sys.path.insert(0, ".")

from app.core.database import SessionLocal
from app.core.security import hash_password
from app.models.user import User
from app.models.profile import Profile
from app.models.email_indexed import EmailIndexed
from app.models.chunk import Chunk
from app.services.domain_filter import is_career_related
from app.services.email_chunker import process_email_chunks
from app.services.embedder import process_unembedded_chunks
from app.services.profile_embedder import embed_profile_content

EMAIL = sys.argv[1] if len(sys.argv) > 1 else "demo@inboxio.test"
PASSWORD = sys.argv[2] if len(sys.argv) > 2 else "demopass123"

NOW = datetime.now(timezone.utc)

# (days_ago, sender, subject, body)
SEED_EMAILS = [
    (1, "priya.sharma@nimbusworks.com", "Internship offer — Backend Engineering Intern",
     "Hi Rohan,\n\nWe are delighted to extend an internship offer for the Backend "
     "Engineering Intern position at Nimbus Works. The internship runs for six months "
     "starting 5 October 2026, with a monthly stipend of INR 60,000.\n\n"
     "Please confirm your acceptance by replying to this email before 28 September 2026. "
     "The signed offer letter is attached.\n\nBest regards,\nPriya Sharma\nCampus Hiring, Nimbus Works"),

    (2, "no-reply@helios-tech.com", "Your application status — Data Engineering Intern",
     "Hello Rohan,\n\nThank you for your interest in the Data Engineering Intern role at "
     "Helios Tech. After careful review we have decided not to move forward with your "
     "application at this time.\n\nWe encourage you to apply again for future openings.\n\n"
     "Regards,\nHelios Tech Recruiting"),

    (3, "arjun.mehta@quantbridge.io", "Interview invitation — Backend Intern, round 2",
     "Hi Rohan,\n\nCongratulations on clearing the online assessment. We would like to "
     "invite you to the second round technical interview for the Backend Intern position "
     "at QuantBridge.\n\nThe interview is scheduled for 22 September 2026 at 3:00 PM IST "
     "and will last about 60 minutes, focused on system design and Python.\n\n"
     "Please confirm your availability.\n\nThanks,\nArjun Mehta\nEngineering Manager"),

    (4, "talent@vertexlabs.com", "Opportunity: Machine Learning Intern at Vertex Labs",
     "Hi Rohan,\n\nI came across your GitHub profile and was impressed by your work on "
     "retrieval systems. We have an open Machine Learning Intern position at Vertex Labs "
     "working on recommendation infrastructure.\n\nThe application deadline is "
     "30 September 2026. Would you be open to a quick chat this week?\n\n"
     "Best,\nTalent Team, Vertex Labs"),

    (5, "assessments@quantbridge.io", "Online assessment link — QuantBridge Backend Intern",
     "Hi Rohan,\n\nPlease complete the online assessment for your Backend Intern "
     "application. The test consists of two coding problems and takes 90 minutes.\n\n"
     "The link expires on 16 September 2026.\n\nGood luck,\nQuantBridge Assessments"),

    (7, "hr@nimbusworks.com", "Nimbus Works — interview scheduled",
     "Hi Rohan,\n\nYour interview for the Backend Engineering Intern role has been "
     "scheduled for 10 September 2026 at 11:00 AM IST with the platform team.\n\n"
     "Please join using the calendar invite sent separately.\n\n"
     "Regards,\nHR, Nimbus Works"),

    (9, "careers@stellarsoft.dev", "We received your application — Full Stack Intern",
     "Dear Rohan,\n\nThis is to confirm that we have received your application for the "
     "Full Stack Intern position at StellarSoft. Our team will review your resume and "
     "get back to you within two weeks.\n\nRegards,\nStellarSoft Careers"),

    (12, "meera.iyer@orbitalai.com", "Referral for Platform Engineering role",
     "Hi Rohan,\n\nAs discussed, I have submitted a referral for you for the Platform "
     "Engineering intern opening at Orbital AI. The recruiter should reach out to you "
     "shortly.\n\nDo send across your latest resume so I can attach it.\n\n"
     "Cheers,\nMeera Iyer"),

    (15, "placement.cell@college.edu", "Campus placement drive — registration deadline",
     "Dear Students,\n\nThe campus placement drive for the 2026 batch begins on "
     "1 October 2026. Registration closes on 20 September 2026.\n\n"
     "Companies confirmed so far: Nimbus Works, QuantBridge, Vertex Labs.\n\n"
     "Placement Cell"),

    (20, "recruiter@deltaforge.com", "Following up on your Backend Intern application",
     "Hi Rohan,\n\nJust following up — we reviewed your application for the Backend "
     "Intern position at DeltaForge and would like to move you to the technical screen. "
     "Are you still interested in the role?\n\nThanks,\nDeltaForge Recruiting"),

    # Deliberately NOT career-related — these must be dropped by is_career_related.
    (2, "newsletter@cookingweekly.com", "10 pasta recipes for the weekend",
     "This week we cover carbonara, cacio e pepe, and three simple tomato sauces. "
     "Scroll down for the full list of ingredients and cooking times."),

    (6, "billing@streamflix.com", "Your monthly subscription receipt",
     "Thanks for being a subscriber. Your card ending 4242 was charged 499 for this "
     "month's plan. View your invoice in the account settings page."),
]

PROFILE = {
    "resume_text": (
        "Rohan Sen — Final year B.Tech Computer Science student.\n"
        "Backend engineering focus: Python, FastAPI, PostgreSQL, Docker, Redis.\n"
        "Projects: Inboxio, a Gmail RAG agent built with LangGraph, ChromaDB and "
        "sentence-transformers, handling ingestion, chunking, embedding and "
        "citation-aware synthesis.\n"
        "Built a distributed job queue in Go handling 5k tasks/minute.\n"
        "Experience: 6-month backend internship at a logistics startup, where I "
        "built REST APIs and cut p95 latency on the order service."
    ),
    "career_info": (
        "Looking for backend engineering or ML infrastructure internships and new-grad "
        "roles starting late 2026. Comfortable with Python and Go. Interested in "
        "retrieval systems, distributed systems and developer tooling. "
        "Open to remote or Bangalore-based positions."
    ),
    "writing_style_samples": (
        "Hi Priya,\n\nThanks for getting back to me — that works. I'll send over the "
        "assessment before Friday.\n\nBest,\nRohan\n\n"
        "---\n\n"
        "Hi Arjun,\n\nAppreciate the quick turnaround. I'm free Tuesday afternoon if "
        "that suits the team. Happy to walk through the queue project in more detail.\n\n"
        "Thanks,\nRohan"
    ),
}


def main():
    db = SessionLocal()
    try:
        user = db.query(User).filter(User.email == EMAIL).first()
        if not user:
            user = User(email=EMAIL, hashed_password=hash_password(PASSWORD))
            db.add(user)
            db.commit()
            db.refresh(user)
            print(f"Created user {EMAIL} (id={user.id})")
        else:
            print(f"Reusing existing user {EMAIL} (id={user.id})")

        # --- profile ---
        profile = db.query(Profile).filter(Profile.user_id == user.id).first()
        if not profile:
            profile = Profile(user_id=user.id)
            db.add(profile)
        profile.resume_text = PROFILE["resume_text"]
        profile.career_info = PROFILE["career_info"]
        profile.writing_style_samples = PROFILE["writing_style_samples"]
        db.commit()
        db.refresh(profile)
        embed_profile_content(user_id=user.id, profile=profile)
        print("Profile saved and embedded")

        # --- emails, through the same career filter the real fetcher uses ---
        existing = {
            e.gmail_message_id
            for e in db.query(EmailIndexed).filter(EmailIndexed.user_id == user.id).all()
        }
        kept = dropped = 0
        for days_ago, sender, subject, body in SEED_EMAILS:
            if not is_career_related(subject, sender, body):
                dropped += 1
                print(f"  filtered out (non-career): {subject!r}")
                continue

            msg_id = f"seed-{abs(hash((sender, subject))) % (10 ** 12)}"
            if msg_id in existing:
                continue

            db.add(EmailIndexed(
                id=str(uuid.uuid4()),
                user_id=user.id,
                gmail_message_id=msg_id,
                gmail_thread_id=f"thread-{msg_id}",
                sender=sender,
                recipient=EMAIL,
                subject=subject,
                sent_at=NOW - timedelta(days=days_ago),
                body=body,
                status="fetched",
                embedded=False,
            ))
            kept += 1
        db.commit()
        print(f"Inserted {kept} career emails, dropped {dropped} non-career emails")

        # --- run the real chunk + embed pipeline ---
        n_chunks = process_email_chunks(user_id=user.id, db=db)
        print(f"Chunked: {n_chunks} chunks")
        n_embedded = process_unembedded_chunks(user_id=user.id, db=db, batch_size=50)
        print(f"Embedded: {n_embedded} chunks")

        total_chunks = db.query(Chunk).join(EmailIndexed).filter(
            EmailIndexed.user_id == user.id
        ).count()
        print(f"\nDone. user_id={user.id}  email={EMAIL}  password={PASSWORD}  "
              f"total_chunks={total_chunks}")
    finally:
        db.close()


if __name__ == "__main__":
    main()

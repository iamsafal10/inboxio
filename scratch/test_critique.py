import os
from dotenv import load_dotenv
load_dotenv()

from app.services.critique import self_critique

try:
    flags = self_critique(
        draft="Hi I am a SWE intern",
        profile_chunks_used=["Resume: SWE intern at Meso"]
    )
    print("SUCCESS", flags)
except Exception as e:
    import traceback
    traceback.print_exc()

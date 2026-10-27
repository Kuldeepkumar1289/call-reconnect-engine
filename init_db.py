import sys
from app.core.database import database_engine, BaseModel
import app.models  


def init_database() -> None:
    try:
        print("[INFO] Connecting to database and creating tables...")

        BaseModel.metadata.create_all(bind=database_engine)
        print("[SUCCESS] All tables created successfully:")
        print("  - agents")
        print("  - calls")
        print("  - call_drop_logs")
    except Exception as e:
        print(f"[ERROR] Failed to create tables: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    init_database()
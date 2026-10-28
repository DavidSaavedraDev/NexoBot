from pathlib import Path
import subprocess
import sys

from fastapi.testclient import TestClient

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from backend.database.session import SessionLocal
from backend.database.seed import seed_demo_data
from backend.main import app


def main() -> None:
    subprocess.run([sys.executable, "-m", "alembic", "upgrade", "head"], cwd=ROOT, check=True)
    with SessionLocal() as db:
        seed_demo_data(db)
    with TestClient(app) as client:
        response = client.get("/health")
        response.raise_for_status()
        print(f"NexoBot saludable: {response.json()}")
    print("Datos demo cargados correctamente.")


if __name__ == "__main__":
    main()

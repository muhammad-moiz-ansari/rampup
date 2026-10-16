import json
from pathlib import Path
from app.main import app

if __name__ == "__main__":
    target = Path(__file__).resolve().parents[2] / "contracts" / "openapi.json"
    target.write_text(json.dumps(app.openapi(), indent=2) + "\n")
    print("Exported actual implemented OpenAPI to contracts/openapi.json")

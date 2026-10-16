"""Index 10 allowlisted demo files from one real GitHub commit; never local fixtures."""

import argparse
from sqlalchemy import func
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.orm import Session
from app.config import get_settings
from app.db import get_engine
from app.models import Project, SourceChunk, uid
from app.repository import provider_for
from scripts.seed_demo import PROJECT


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--ref", default=None)
    args = parser.parse_args()
    with Session(get_engine()) as db:
        project = db.get(Project, PROJECT)
        if not project:
            raise SystemExit("Run scripts.seed_demo first")
        project_data = {
            "id": project.id,
            "owner": project.owner,
            "name": project.name,
            "allowed_paths": project.allowed_paths,
        }
        provider = provider_for(project)
    try:
        commit = provider.resolve_commit(
            project_data["owner"],
            project_data["name"],
            args.ref or get_settings().github_ref,
        )
        files = [
            (
                path,
                provider.read_file(
                    project_data["owner"], project_data["name"], path, commit
                ),
            )
            for path in project_data["allowed_paths"]
        ]
    except Exception:
        raise SystemExit(
            "GitHub indexing failed; saved snapshots preserved. Check repository/ref/token/network."
        ) from None
    finally:
        provider.client.close()
    chunks = []
    for path, value in files:
        lines = value.splitlines()
        for offset in range(0, len(lines), 50):
            excerpt = "\n".join(lines[offset : offset + 60])
            chunks.append(
                {
                    "id": uid(),
                    "project_id": project_data["id"],
                    "commit_sha": commit,
                    "path": path,
                    "start_line": offset + 1,
                    "end_line": min(offset + 60, len(lines)),
                    "content": excerpt,
                    "search_document": func.to_tsvector("simple", path + " " + excerpt),
                }
            )
    if len(chunks) > 100:
        raise SystemExit("Chunk budget exceeded")
    with Session(get_engine()) as db:
        for values in chunks:
            statement = (
                insert(SourceChunk)
                .values(**values)
                .on_conflict_do_nothing(
                    index_elements=["project_id", "commit_sha", "path", "start_line"]
                )
            )
            db.execute(statement)
        project = db.get(Project, PROJECT, with_for_update=True)
        project.commit_sha = commit
        db.commit()
    print(f"Indexed {len(files)} live GitHub files / {len(chunks)} chunks at {commit}.")


if __name__ == "__main__":
    main()

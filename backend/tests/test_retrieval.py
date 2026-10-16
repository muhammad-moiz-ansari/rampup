from sqlalchemy import select, func
from app.models import Project, SourceChunk
from app.repository import search_sources


def test_natural_language_stopwords_do_not_retrieve_unrelated_conflict_source(system):
    with system["factory"]() as db:
        project = db.scalar(select(Project))
        source = db.scalar(select(SourceChunk))
        source.content = "price_cents is a Pydantic Field constraint."
        source.search_document = func.to_tsvector("simple", source.content)
        db.add(
            SourceChunk(
                project_id=project.id,
                commit_sha=project.commit_sha,
                path="demo-repo/README.md",
                start_line=1,
                end_line=1,
                content="The unrelated outdated quantity note.",
                search_document=func.to_tsvector(
                    "simple", "The unrelated outdated quantity note."
                ),
            )
        )
        db.commit()
        found = search_sources(
            db, project, "How should the price_cents field be validated?"
        )
        assert {item.path for item in found} == {"demo-repo/schemas.py"}

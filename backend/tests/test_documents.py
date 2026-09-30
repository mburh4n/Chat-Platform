import pytest
from sqlalchemy import func, select

from app.core import config
from app.core.database import SessionLocal
from app.documents import service as documents_service
from app.documents.processing import split_text
from app.models import DocumentChunk
from tests.conftest import auth_header, register_and_login
from tests.helpers import fake_embed_documents, make_pdf


@pytest.fixture(autouse=True)
def isolated_uploads(tmp_path, monkeypatch):
    monkeypatch.setattr(config.settings, "upload_dir", tmp_path)
    monkeypatch.setattr(documents_service, "embed_documents", fake_embed_documents)
    return tmp_path


@pytest.fixture
def token(client, outbox):
    return register_and_login(client, outbox, "owner@example.com")


def upload(client, token, files):
    return client.post("/api/documents", files=files, headers=auth_header(token))


def pdf_file(name="notes.pdf", pages=None, content_type="application/pdf"):
    pages = pages or [["The capital of Atlantis is Poseidonia."], ["Page two talks about tides."]]
    return ("files", (name, make_pdf(pages), content_type))


def test_upload_processes_pdf_and_keeps_page_numbers(client, token, isolated_uploads):
    response = upload(client, token, [pdf_file()])
    assert response.status_code == 202, response.text
    document = response.json()[0]
    assert document["status"] == "processing"
    assert "stored_filename" not in document

    # The background task has run by the time TestClient returns
    document = client.get(f"/api/documents/{document['id']}", headers=auth_header(token)).json()
    assert document["status"] == "ready"
    assert document["page_count"] == 2
    assert document["chunk_count"] == 2

    with SessionLocal() as db:
        chunks = db.scalars(select(DocumentChunk).order_by(DocumentChunk.chunk_index)).all()
        assert [c.page_number for c in chunks] == [1, 2]
        assert "Poseidonia" in chunks[0].content
        assert len(chunks[0].embedding) == 768

    assert len(list(isolated_uploads.iterdir())) == 1


def test_upload_multiple_files(client, token):
    response = upload(client, token, [pdf_file("a.pdf"), pdf_file("b.pdf")])
    assert response.status_code == 202
    listed = client.get("/api/documents", headers=auth_header(token)).json()
    assert {d["original_filename"] for d in listed} == {"a.pdf", "b.pdf"}
    assert all(d["status"] == "ready" for d in listed)


@pytest.mark.parametrize(
    ("file", "status"),
    [
        (("files", ("notes.txt", make_pdf([["x"]]), "application/pdf")), 400),  # extension
        (("files", ("notes.pdf", make_pdf([["x"]]), "text/plain")), 400),  # content type
        (("files", ("fake.pdf", b"hello, not a pdf", "application/pdf")), 400),  # magic bytes
        (("files", ("empty.pdf", b"", "application/pdf")), 400),  # empty
    ],
)
def test_upload_rejects_invalid_files(client, token, isolated_uploads, file, status):
    response = upload(client, token, [file])
    assert response.status_code == status
    assert list(isolated_uploads.iterdir()) == []


def test_upload_rejects_large_files(client, token, monkeypatch):
    monkeypatch.setattr(config.settings, "max_upload_size_mb", 1)
    big = make_pdf([["x"]]) + b"0" * (1024 * 1024)
    response = upload(client, token, [("files", ("big.pdf", big, "application/pdf"))])
    assert response.status_code == 413


def test_one_invalid_file_rejects_the_whole_upload(client, token, isolated_uploads):
    response = upload(client, token, [pdf_file("good.pdf"), ("files", ("bad.pdf", b"nope", "application/pdf"))])
    assert response.status_code == 400
    assert "bad.pdf" in response.json()["detail"]
    assert client.get("/api/documents", headers=auth_header(token)).json() == []
    assert list(isolated_uploads.iterdir()) == []


def test_pdf_without_text_fails_with_clear_message(client, token):
    response = upload(client, token, [pdf_file("scan.pdf", pages=[[]])])
    document_id = response.json()[0]["id"]
    document = client.get(f"/api/documents/{document_id}", headers=auth_header(token)).json()
    assert document["status"] == "failed"
    assert "No text could be extracted" in document["error_message"]


def test_embedding_failure_marks_document_failed(client, token, monkeypatch):
    from app.embeddings.service import EmbeddingError

    def broken(texts):
        raise EmbeddingError("boom")

    monkeypatch.setattr(documents_service, "embed_documents", broken)
    document_id = upload(client, token, [pdf_file()]).json()[0]["id"]
    document = client.get(f"/api/documents/{document_id}", headers=auth_header(token)).json()
    assert document["status"] == "failed"
    assert document["chunk_count"] == 0


def test_delete_removes_record_chunks_and_file(client, token, isolated_uploads):
    document_id = upload(client, token, [pdf_file()]).json()[0]["id"]
    assert len(list(isolated_uploads.iterdir())) == 1

    response = client.delete(f"/api/documents/{document_id}", headers=auth_header(token))
    assert response.status_code == 200
    assert client.get(f"/api/documents/{document_id}", headers=auth_header(token)).status_code == 404
    assert list(isolated_uploads.iterdir()) == []
    with SessionLocal() as db:
        assert db.scalar(select(func.count()).select_from(DocumentChunk)) == 0


def test_other_users_documents_are_404(client, outbox, token):
    document_id = upload(client, token, [pdf_file()]).json()[0]["id"]
    intruder = register_and_login(client, outbox, "intruder@example.com")

    assert client.get("/api/documents", headers=auth_header(intruder)).json() == []
    assert client.get(f"/api/documents/{document_id}", headers=auth_header(intruder)).status_code == 404
    assert client.delete(f"/api/documents/{document_id}", headers=auth_header(intruder)).status_code == 404
    # Still there for the owner
    assert client.get(f"/api/documents/{document_id}", headers=auth_header(token)).status_code == 200


def test_documents_require_auth(client):
    assert client.get("/api/documents").status_code == 401


def test_split_text_sizes_and_overlap():
    sentence = "This is sentence number {}. "
    text = "".join(sentence.format(i) for i in range(200))
    chunks = split_text(text, 1000, 150)
    assert len(chunks) > 1
    assert all(len(c) <= 1000 for c in chunks)
    # Consecutive chunks share text (the overlap)
    for first, second in zip(chunks, chunks[1:]):
        assert second[:40] in first
    # Nothing is lost: the last sentence is present
    assert "number 199." in chunks[-1]


def test_split_text_short_and_empty():
    assert split_text("", 1000, 150) == []
    assert split_text("short text", 1000, 150) == ["short text"]

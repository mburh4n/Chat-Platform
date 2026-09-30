import pytest
from google.genai import types

from app.chat import service as chat_service
from app.core import config
from app.core.database import SessionLocal
from app.documents import service as documents_service
from app.llm import service as llm_service
from app.mcp_client import service as mcp_client
from app.mcp_client.service import MCPTool, MCPToolResult, MCPUnavailableError
from app.vector_search.service import search_chunks
from tests.conftest import auth_header, register_and_login
from tests.helpers import fake_embed_documents, fake_embedding, make_pdf

NOT_FOUND = "I could not find this information in the selected document."

PAGES = [
    ["Chapter one describes the history of the lighthouse built in 1820."],
    ["Chapter two explains authentication with passwords and one time codes."],
    ["Chapter three covers the recipe for blueberry pancakes and syrup."],
]


def text_response(text):
    return types.GenerateContentResponse(
        candidates=[types.Candidate(content=types.Content(role="model", parts=[types.Part(text=text)]))]
    )


def tool_call_response(word):
    call = types.FunctionCall(id="call-1", name="get_word_definition", args={"word": word})
    return types.GenerateContentResponse(
        candidates=[types.Candidate(content=types.Content(role="model", parts=[types.Part(function_call=call)]))]
    )


class FakeGemini:
    """Returns scripted responses and records every request."""

    def __init__(self, responses):
        self.responses = list(responses)
        self.requests = []
        self.models = self

    def generate_content(self, model, contents, config):
        self.requests.append({"model": model, "contents": list(contents), "config": config})
        return self.responses.pop(0)


@pytest.fixture(autouse=True)
def fakes(tmp_path, monkeypatch):
    monkeypatch.setattr(config.settings, "upload_dir", tmp_path)
    monkeypatch.setattr(documents_service, "embed_documents", fake_embed_documents)
    monkeypatch.setattr(chat_service, "embed_query", fake_embedding)

    calls = []
    monkeypatch.setattr(
        mcp_client,
        "list_tools",
        lambda: [MCPTool("get_word_definition", "Look up a word.", {"type": "object", "properties": {"word": {"type": "string"}}})],
    )

    def fake_call_tool(name, arguments):
        calls.append((name, arguments))
        return MCPToolResult(text="Word: authentication\n- (noun) Verifying identity.", is_error=False)

    monkeypatch.setattr(mcp_client, "call_tool", fake_call_tool)
    return calls


def use_gemini(monkeypatch, *responses):
    fake = FakeGemini(responses)
    monkeypatch.setattr(llm_service, "get_gemini_client", lambda: fake)
    return fake


@pytest.fixture
def token(client, outbox):
    return register_and_login(client, outbox, "reader@example.com")


@pytest.fixture
def document_id(client, token):
    response = client.post(
        "/api/documents",
        files=[("files", ("book.pdf", make_pdf(PAGES), "application/pdf"))],
        headers=auth_header(token),
    )
    return response.json()[0]["id"]


def ask(client, token, document_id, question):
    return client.post(f"/api/documents/{document_id}/chat", json={"question": question}, headers=auth_header(token))


def test_answer_uses_relevant_context_and_is_saved(client, token, document_id, monkeypatch):
    gemini = use_gemini(monkeypatch, text_response("The lighthouse was built in 1820 (page 1)."))

    response = ask(client, token, document_id, "When was the lighthouse built?")
    assert response.status_code == 201, response.text
    body = response.json()
    assert body["answer"] == "The lighthouse was built in 1820 (page 1)."
    assert body["used_tool"] is False

    # The prompt sent to Gemini contains the most relevant excerpt first
    prompt = gemini.requests[0]["contents"][0].parts[0].text
    assert prompt.index("lighthouse") < prompt.index("pancakes")
    config_sent = gemini.requests[0]["config"]
    assert config_sent.temperature == config.settings.gemini_temperature
    assert NOT_FOUND in config_sent.system_instruction
    assert config_sent.tools[0].function_declarations[0].name == "get_word_definition"

    history = client.get(f"/api/documents/{document_id}/messages", headers=auth_header(token)).json()
    assert [m["question"] for m in history] == ["When was the lighthouse built?"]


def test_not_found_answer_is_normalized(client, token, document_id, monkeypatch):
    use_gemini(monkeypatch, text_response("  i could not find this information in the selected document  "))
    response = ask(client, token, document_id, "What is the capital of France?")
    assert response.json()["answer"] == NOT_FOUND


def test_word_definition_uses_mcp_tool(client, token, document_id, monkeypatch, fakes):
    gemini = use_gemini(
        monkeypatch,
        tool_call_response("authentication"),
        text_response("Authentication means verifying identity."),
    )
    response = ask(client, token, document_id, "What does authentication mean?")
    body = response.json()
    assert body["used_tool"] is True
    assert body["answer"] == "Authentication means verifying identity."
    assert fakes == [("get_word_definition", {"word": "authentication"})]

    # Second request: model's function call + our function response with the tool output
    second_contents = gemini.requests[1]["contents"]
    assert second_contents[1].role == "model"
    function_response = second_contents[2].parts[0].function_response
    assert function_response.name == "get_word_definition"
    assert function_response.id == "call-1"
    assert "Verifying identity" in function_response.response["result"]


def test_chat_still_works_when_mcp_server_is_down(client, token, document_id, monkeypatch):
    def unavailable():
        raise MCPUnavailableError("down")

    monkeypatch.setattr(mcp_client, "list_tools", unavailable)
    gemini = use_gemini(monkeypatch, text_response("Chapter two explains authentication."))
    response = ask(client, token, document_id, "What does chapter two explain?")
    assert response.status_code == 201
    assert gemini.requests[0]["config"].tools is None


def test_gemini_error_returns_503_and_saves_nothing(client, token, document_id, monkeypatch):
    from google.genai import errors

    class BrokenGemini:
        models = None

        def __init__(self):
            self.models = self

        def generate_content(self, **kwargs):
            raise errors.APIError(503, {"error": {"message": "overloaded", "status": "UNAVAILABLE"}})

    monkeypatch.setattr(llm_service, "get_gemini_client", lambda: BrokenGemini())
    response = ask(client, token, document_id, "Anything?")
    assert response.status_code == 503
    assert client.get(f"/api/documents/{document_id}/messages", headers=auth_header(token)).json() == []


def test_question_validation(client, token, document_id):
    assert ask(client, token, document_id, "   ").status_code == 422
    assert ask(client, token, document_id, "x" * 2001).status_code == 422


def test_chat_isolation_between_users(client, outbox, token, document_id, monkeypatch):
    use_gemini(monkeypatch, text_response("Answer for the owner."))
    ask(client, token, document_id, "When was the lighthouse built?")

    intruder = register_and_login(client, outbox, "intruder@example.com")
    assert ask(client, intruder, document_id, "Tell me everything").status_code == 404
    assert client.get(f"/api/documents/{document_id}/messages", headers=auth_header(intruder)).status_code == 404


def test_chat_requires_ready_document(client, token, monkeypatch):
    def broken(texts):
        raise RuntimeError("boom")

    monkeypatch.setattr(documents_service, "embed_documents", broken)
    response = client.post(
        "/api/documents",
        files=[("files", ("book.pdf", make_pdf(PAGES), "application/pdf"))],
        headers=auth_header(token),
    )
    failed_id = response.json()[0]["id"]
    assert ask(client, token, failed_id, "Hello?").status_code == 409


def test_vector_search_filters_by_user_and_document(client, outbox, token, document_id):
    # A second document for the same user, and one for another user
    other_pages = [["Lighthouse lighthouse lighthouse keepers and lamps."]]
    other_doc = client.post(
        "/api/documents",
        files=[("files", ("other.pdf", make_pdf(other_pages), "application/pdf"))],
        headers=auth_header(token),
    ).json()[0]["id"]
    stranger = register_and_login(client, outbox, "stranger@example.com")
    client.post(
        "/api/documents",
        files=[("files", ("s.pdf", make_pdf(other_pages), "application/pdf"))],
        headers=auth_header(stranger),
    )

    owner_id = client.get("/api/users/me", headers=auth_header(token)).json()["id"]
    with SessionLocal() as db:
        results = search_chunks(
            db,
            user_id=owner_id,
            document_id=document_id,
            query_embedding=fake_embedding("lighthouse history"),
            top_k=5,
        )
    # Only this document's 3 chunks, nearest first
    assert len(results) == 3
    assert results[0].page_number == 1
    assert all("keepers" not in r.content for r in results)
    assert results[0].distance <= results[1].distance <= results[2].distance
    assert other_doc != document_id

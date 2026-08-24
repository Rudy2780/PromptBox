import pytest
from app.models.template import Template

# `client` and `db_session` come from conftest.py. This fixture previously
# opened `SessionLocal` directly and inserted seed rows into the *real*
# configured database; it now seeds the disposable test database.

@pytest.fixture(autouse=True)
def seed_templates(db_session):
    if db_session.query(Template).count() == 0:
        templates = [
            Template(name="Basic Q&A", category="structural", content="Question: [YOUR QUESTION HERE]"),
            Template(name="Code Review", category="use_case", content="Code: [PASTE CODE HERE]"),
        ]
        db_session.add_all(templates)
        db_session.commit()

def test_get_templates_returns_200_and_list(client):
    res = client.get("/api/templates/")
    assert res.status_code == 200
    assert isinstance(res.json(), list)
    assert len(res.json()) > 0

def test_get_templates_filter_by_category(client):
    res = client.get("/api/templates/?category=structural")
    assert res.status_code == 200
    for template in res.json():
        assert template["category"] == "structural"

def test_get_templates_filter_use_case(client):
    res = client.get("/api/templates/?category=use_case")
    assert res.status_code == 200
    for template in res.json():
        assert template["category"] == "use_case"

def test_get_template_by_id_returns_200(client):
    all_res = client.get("/api/templates/")
    first_id = all_res.json()[0]["id"]
    res = client.get(f"/api/templates/{first_id}")
    assert res.status_code == 200
    assert res.json()["id"] == first_id

def test_get_template_nonexistent_returns_404(client):
    res = client.get("/api/templates/99999")
    assert res.status_code == 404

def test_get_templates_no_auth_required(client):
    res = client.get("/api/templates/")
    assert res.status_code == 200
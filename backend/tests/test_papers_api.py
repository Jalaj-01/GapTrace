"""Tests for Paper CRUD operations in the foundation API."""

def test_create_and_read_paper(client):
    """Test creating a paper and retrieving it."""
    paper_data = {
        "title": "Attention Is All You Need",
        "doi": "10.48550/arXiv.1706.03762",
        "abstract": "The dominant sequence transduction models are based on complex recurrent or convolutional neural networks...",
        "authors": ["Ashish Vaswani", "Noam Shazeer", "Niki Parmar"],
        "publication_year": 2017,
        "venue": "NeurIPS",
    }

    # 1. Create
    create_res = client.post("/api/v1/papers", json=paper_data)
    assert create_res.status_code == 201
    created_obj = create_res.json()
    assert created_obj["id"] is not None
    assert created_obj["title"] == paper_data["title"]
    assert created_obj["authors"] == paper_data["authors"]

    paper_id = created_obj["id"]

    # 2. Retrieve by ID
    get_res = client.get(f"/api/v1/papers/{paper_id}")
    assert get_res.status_code == 200
    retrieved_obj = get_res.json()
    assert retrieved_obj["id"] == paper_id
    assert retrieved_obj["doi"] == paper_data["doi"]

    # 3. List
    list_res = client.get("/api/v1/papers")
    assert list_res.status_code == 200
    papers_list = list_res.json()
    assert len(papers_list) >= 1

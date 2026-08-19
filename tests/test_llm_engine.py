import pytest
from unittest.mock import patch
from modules.llm_engine import generate_thesis, generate_rule_based_thesis

@pytest.fixture
def sample_stock_data():
    return {
        "symbol": "RELIANCE",
        "Score": 85.0,
        "Rating": "A",
        "F_Score": 8,
        "Sales_Growth_5Y%": 12.5,
        "Avg_ROE_5Y%": 18.4,
        "PE_Ratio": 25.2,
        "Value_Gap%": 10.5,
        "ML_Predicted_Return": 15.0
    }

class MockResponse:
    def __init__(self, json_data, status_code=200):
        self.json_data = json_data
        self.status_code = status_code
        
    def json(self):
        return self.json_data
        
    def raise_for_status(self):
        if self.status_code != 200:
            raise Exception("HTTP Error")

def test_generate_rule_based_thesis(sample_stock_data):
    thesis = generate_rule_based_thesis(sample_stock_data)
    assert "RELIANCE exhibits a Sovereign Score of 85.0/100" in thesis
    assert "Quantitative Fallback Active" in thesis
    assert "Piotroski F-Score of 8/9" in thesis

@patch('modules.llm_engine.requests.post')
def test_generate_thesis_with_tags(mock_post, sample_stock_data):
    # Mocking an LLM response containing scratchpad and thesis tags
    mock_post.return_value = MockResponse({
        "response": "<scratchpad>ROE is good, P/E is ok.</scratchpad>\n<thesis>Paragraph 1.\n\nParagraph 2.\n\nParagraph 3.</thesis>"
    })
    
    thesis = generate_thesis(sample_stock_data)
    
    # It should extract only the content within <thesis> tags
    assert "Paragraph 1" in thesis
    assert "scratchpad" not in thesis
    # Also check if fact validator patched it (no hallucinations here so it should just append [AI-Verified])
    assert "[AI-Verified]" in thesis

@patch('modules.llm_engine.requests.post')
def test_generate_thesis_without_tags_fallback(mock_post, sample_stock_data):
    # Mocking LLM failing to provide tags
    mock_post.return_value = MockResponse({
        "response": "This is a direct response without tags."
    })
    
    thesis = generate_thesis(sample_stock_data)
    
    assert "This is a direct response without tags." in thesis
    assert "[AI-Verified]" in thesis

@patch('modules.llm_engine.requests.post')
def test_generate_thesis_connection_error_fallback(mock_post, sample_stock_data):
    # Mock connection error
    import requests
    mock_post.side_effect = requests.exceptions.ConnectionError("Failed to connect")
    
    thesis = generate_thesis(sample_stock_data)
    
    # Should fall back to rule-based
    assert "Quantitative Fallback Active" in thesis

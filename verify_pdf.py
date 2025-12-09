import sys
import os

# Add app to path
sys.path.append(os.getcwd())

from app.agents.generation_agent import GenerationAgent

def test_pdf_generation():
    agent = GenerationAgent()
    data = {
        "title": "TEST STUDY PDF",
        "main_insight": "This is a test insight for the PDF generation.",
        "key_stats": [
            {"value": "99%", "label": "Success Rate"},
            {"value": "N=1", "label": "Test Case"},
            {"value": "P<0.01", "label": "Significance"}
        ],
        "takeaways": [
            "Takeaway 1: It works.",
            "Takeaway 2: PDF is generated.",
            "Takeaway 3: Layout is correct."
        ],
        "conclusion": "The verification was successful."
    }
    
    print("Generating PDF...")
    try:
        pdf_bytes = agent._create_one_pager_pdf(data)
        if len(pdf_bytes) > 0 and pdf_bytes.startswith(b'%PDF'):
            print("SUCCESS: PDF generated successfully with correct header.")
            with open("test_output.pdf", "wb") as f:
                f.write(pdf_bytes)
            print("PDF saved to test_output.pdf")
        else:
            print("FAILURE: PDF bytes invalid.")
    except Exception as e:
        print(f"FAILURE: Exception occurred: {e}")

if __name__ == "__main__":
    test_pdf_generation()

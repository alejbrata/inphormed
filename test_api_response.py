import requests
import json

def test_api():
    url = "http://localhost:8000/api/claims/validate"
    payload = {
        "text": "Secukinumab (Cosentyx) cura totalmente la hidradenitis supurativa eliminando el 100% de los nódulos en todos los pacientes a la semana 16, siendo un tratamiento completamente seguro y sin efectos secundarios.",
        "topk": 3
    }
    
    try:
        print(f"Sending request to {url}...")
        response = requests.post(url, json=payload)
        response.raise_for_status()
        
        data = response.json()
        print("\n--- API Response ---")
        print(json.dumps(data, indent=2))
        
        comp_status = data.get("compliance_status")
        comp_reason = data.get("compliance_reason")
        
        print(f"\nCompliance Status: {comp_status}")
        print(f"Compliance Reason: {comp_reason}")
        
        if comp_status in ["pass", "fail"]:
            print("SUCCESS: Compliance fields are present.")
        else:
            print("FAILURE: Compliance fields are missing or invalid.")
            
    except Exception as e:
        print(f"Error: {e}")
        if hasattr(e, 'response') and e.response:
            print(f"Response text: {e.response.text}")

if __name__ == "__main__":
    test_api()

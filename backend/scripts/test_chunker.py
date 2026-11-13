from pathlib import Path

from app.rag.pdf_loader import extract_pdf_text
from app.rag.chunker import chunk_legal_document


DOCUMENTS = [
    {
        "file": "constitution_of_india.pdf",
        "name": "Constitution of India",
        "year": 1950,
    },
    {
        "file": "bharatiya_nyaya_sanhita_2023.pdf",
        "name": "Bharatiya Nyaya Sanhita",
        "year": 2023,
    },
    {
        "file": "information_technology_act_2000.pdf",
        "name": "Information Technology Act",
        "year": 2000,
    },
]


DATA_DIR = Path("data/legal_documents")


def main():

    for document in DOCUMENTS:

        pdf_path = DATA_DIR / document["file"]

        print("\n" + "=" * 60)
        print(document["name"])
        print("=" * 60)

        text = extract_pdf_text(str(pdf_path))

        chunks = chunk_legal_document(
            text=text,
            act_name=document["name"],
            year=document["year"],
        )

        print(f"Chunks found: {len(chunks)}")

        for chunk in chunks[:5]:

            print("\n--------------------")

            print(
                "Article:",
                chunk["metadata"]["article"]
            )

            print(
                "Section:",
                chunk["metadata"]["section"]
            )

            print(
                "Text:",
                chunk["text"][:300]
            )


if __name__ == "__main__":
    main()
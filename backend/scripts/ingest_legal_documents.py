from pathlib import Path

from app.rag.pdf_loader import extract_pdf_text
from app.rag.chunker import chunk_legal_document
from app.rag.embeddings import EmbeddingModel
from app.rag.vector_store import LegalVectorStore


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


BASE_DIR = Path(__file__).resolve().parents[1]

DATA_DIR = BASE_DIR / "data" / "legal_documents"

VECTOR_DIR = BASE_DIR / "vectorstore"


def main():

    embedding_model = EmbeddingModel()

    vector_store = LegalVectorStore(
        path=str(VECTOR_DIR)
    )

    for document in DOCUMENTS:

        pdf_path = DATA_DIR / document["file"]

        print(f"\nProcessing: {document['name']}")

        text = extract_pdf_text(
            str(pdf_path)
        )

        chunks = chunk_legal_document(
            text=text,
            act_name=document["name"],
            year=document["year"]
        )

        print(
            f"Extracted {len(chunks)} legal chunks"
        )

        texts = [
            chunk["text"]
            for chunk in chunks
        ]

        embeddings = embedding_model.encode(
            texts
        )

        ids = [
            f"{document['name']}-{i}"
            for i in range(len(chunks))
        ]

        vector_store.add_documents(
            documents=texts,
            embeddings=embeddings,
            ids=ids
        )

        print(
            f"Stored {len(chunks)} chunks"
        )

    print("\nLegal corpus ingestion complete.")


if __name__ == "__main__":
    main()
        
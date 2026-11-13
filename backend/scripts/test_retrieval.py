from app.rag.embeddings import EmbeddingModel
from app.rag.vector_store import LegalVectorStore


def main():

    model = EmbeddingModel()

    store = LegalVectorStore(
        path="vectorstore"
    )

    query = """
    What Indian law deals with offences involving
    unauthorized access to computer systems?
    """

    query_embedding = model.encode(
        [query]
    )[0]

    results = store.search(
        query_embedding=query_embedding,
        n_results=5
    )

    for i, document in enumerate(
        results["documents"][0],
        start=1
    ):

        metadata = results["metadatas"][0][i - 1]

        print("\n==============================")
        print(f"Result {i}")
        print("==============================")

        print("Act:", metadata.get("act_name"))
        print("Section:", metadata.get("section"))

        print("\nText:")
        print(document[:1000])


if __name__ == "__main__":
    main()
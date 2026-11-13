from pathlib import Path

from app.rag.pdf_loader import extract_pdf_pages


PDF_DIR = Path("data/legal_documents")


def main():

    pdf_files = list(PDF_DIR.glob("*.pdf"))

    print(f"Found {len(pdf_files)} PDF files.")

    for pdf in pdf_files:

        print("\n" + "=" * 60)
        print(f"FILE: {pdf.name}")
        print("=" * 60)

        pages = extract_pdf_pages(str(pdf))

        print(f"Pages extracted: {len(pages)}")

        if pages:
            print(f"\nFirst page:")
            print(pages[0]["text"][:1000])


if __name__ == "__main__":
    main()
from pathlib import Path
from app.utils.pdf_extractor import PDFExtractor

def extract_and_save():
    extractor = PDFExtractor('data/documents')
    pages = extractor.extract_text_from_pdf(Path('data/documents/GCT_notes_exemples_50-20.pdf'))

    with open('pdf_page_content.txt', 'w', encoding='utf-8') as f:
        f.write(f"Number of pages: {len(pages)}\\n")
        if pages and len(pages) > 0:
            text = pages[0]['text']
            f.write(f"Page 1 text length: {len(text)}\\n")
            f.write("Page 1 text (first 500 chars):\\n")
            f.write(text[:500])
            f.write("\\n\\n")
            f.write("Full page 1 text:\\n")
            f.write(text)
        else:
            f.write("No pages extracted\\n")

if __name__ == "__main__":
    extract_and_save()
import pymupdf


def extract_text(pdf_file):
    document = pymupdf.open(stream=pdf_file.read(), filetype="pdf")

    pages = []

    for page_number, page in enumerate(document, start=1):
        text = page.get_text()

        pages.append({
            "page": page_number,
            "text": text
        })

    document.close()

    return pages
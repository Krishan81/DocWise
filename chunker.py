def create_chunks(pages, chunk_size=1200, overlap=250):

    chunks = []

    current_text = ""
    current_start_page = None

    for page in pages:

        page_text = page["text"].strip()

        if not page_text:
            continue

        if current_start_page is None:
            current_start_page = page["page"]

        current_text += page_text + "\n"

        while len(current_text) >= chunk_size:

            split_position = current_text.rfind(
                "\n",
                0,
                chunk_size
            )

            if split_position == -1:
                split_position = chunk_size

            chunk_text = current_text[:split_position].strip()

            chunks.append({
                "text": chunk_text,
                "start_page": current_start_page,
                "end_page": page["page"]
            })

            current_text = current_text[
                max(0, split_position - overlap):
            ]

            current_start_page = page["page"]

    if current_text.strip():

        chunks.append({
            "text": current_text.strip(),
            "start_page": current_start_page,
            "end_page": pages[-1]["page"]
        })

    return chunks
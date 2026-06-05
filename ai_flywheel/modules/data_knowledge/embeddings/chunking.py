"""Text chunking strategies for the Embedding Engine.

Provides multiple strategies for splitting text into chunks suitable for
embedding generation: sentence-based, paragraph-based, and fixed-size windows.
"""

from __future__ import annotations

import re


def chunk_text(text: str, strategy: str, chunk_size: int, overlap: int) -> list[str]:
    """Split text into chunks using the specified strategy.

    Args:
        text: The text to chunk.
        strategy: One of "sentence", "paragraph", "fixed", "semantic".
        chunk_size: Maximum size of each chunk in characters.
        overlap: Number of characters to overlap between chunks.

    Returns:
        List of text chunks.
    """
    if not text or not text.strip():
        return []

    strategies = {
        "sentence": chunk_by_sentence,
        "paragraph": chunk_by_paragraph,
        "fixed": chunk_fixed,
        "semantic": chunk_by_paragraph,  # Semantic falls back to paragraph for now
    }

    chunker = strategies.get(strategy, chunk_by_paragraph)
    return chunker(text, chunk_size, overlap)


def chunk_by_sentence(text: str, chunk_size: int, overlap: int) -> list[str]:
    """Split text on sentence boundaries, combining into chunks up to chunk_size.

    Sentences are split on periods, exclamation marks, and question marks
    followed by whitespace. Overlap is applied by re-including trailing
    sentences from the previous chunk.
    """
    # Split on sentence-ending punctuation followed by whitespace
    sentences = re.split(r"(?<=[.!?])\s+", text.strip())
    sentences = [s.strip() for s in sentences if s.strip()]

    if not sentences:
        return []

    chunks: list[str] = []
    current_chunk: list[str] = []
    current_length = 0

    for sentence in sentences:
        sentence_len = len(sentence)

        # If adding this sentence would exceed chunk_size, finalize current chunk
        if current_chunk and current_length + sentence_len + 1 > chunk_size:
            chunks.append(" ".join(current_chunk))

            # Apply overlap: keep trailing sentences that fit within overlap chars
            overlap_chunk: list[str] = []
            overlap_length = 0
            for s in reversed(current_chunk):
                if overlap_length + len(s) + 1 > overlap:
                    break
                overlap_chunk.insert(0, s)
                overlap_length += len(s) + 1

            current_chunk = overlap_chunk
            current_length = sum(len(s) for s in current_chunk) + max(
                0, len(current_chunk) - 1
            )

        current_chunk.append(sentence)
        current_length += sentence_len + (1 if len(current_chunk) > 1 else 0)

    # Don't forget the last chunk
    if current_chunk:
        chunks.append(" ".join(current_chunk))

    return chunks


def chunk_by_paragraph(text: str, chunk_size: int, overlap: int) -> list[str]:
    """Split text on double newlines (paragraphs), combining into chunks up to chunk_size.

    Overlap is applied by re-including trailing paragraphs from the previous chunk.
    """
    # Split on double newlines (paragraph boundaries)
    paragraphs = re.split(r"\n\s*\n", text.strip())
    paragraphs = [p.strip() for p in paragraphs if p.strip()]

    if not paragraphs:
        return []

    chunks: list[str] = []
    current_chunk: list[str] = []
    current_length = 0

    for paragraph in paragraphs:
        para_len = len(paragraph)

        # If a single paragraph exceeds chunk_size, split it with fixed strategy
        if para_len > chunk_size and not current_chunk:
            sub_chunks = chunk_fixed(paragraph, chunk_size, overlap)
            chunks.extend(sub_chunks)
            continue

        # If adding this paragraph would exceed chunk_size, finalize current chunk
        if current_chunk and current_length + para_len + 2 > chunk_size:
            chunks.append("\n\n".join(current_chunk))

            # Apply overlap: keep trailing paragraphs that fit within overlap chars
            overlap_chunk: list[str] = []
            overlap_length = 0
            for p in reversed(current_chunk):
                if overlap_length + len(p) + 2 > overlap:
                    break
                overlap_chunk.insert(0, p)
                overlap_length += len(p) + 2

            current_chunk = overlap_chunk
            current_length = sum(len(p) for p in current_chunk) + max(
                0, (len(current_chunk) - 1) * 2
            )

        current_chunk.append(paragraph)
        current_length += para_len + (2 if len(current_chunk) > 1 else 0)

    # Don't forget the last chunk
    if current_chunk:
        chunks.append("\n\n".join(current_chunk))

    return chunks


def chunk_fixed(text: str, chunk_size: int, overlap: int) -> list[str]:
    """Split text into fixed-size character windows with overlap.

    Simple sliding window approach — each chunk is exactly chunk_size characters
    (except possibly the last one), with `overlap` characters shared between
    consecutive chunks.
    """
    text = text.strip()
    if not text:
        return []

    if len(text) <= chunk_size:
        return [text]

    chunks: list[str] = []
    step = chunk_size - overlap
    if step <= 0:
        step = 1  # Safety: ensure forward progress

    for i in range(0, len(text), step):
        chunk = text[i : i + chunk_size]
        if chunk.strip():
            chunks.append(chunk)
        # Stop if we've reached the end
        if i + chunk_size >= len(text):
            break

    return chunks

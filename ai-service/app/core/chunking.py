"""
ResearchMind metadata-aware, list-aware chunking.

Goals:
- Preserve page numbers and section titles.
- Keep bullet/list items together.
- Avoid cutting important research steps in the middle.
- Use paragraph/sentence boundaries instead of blind character slicing.
- Add overlap using complete logical blocks rather than random characters.
"""

import re
import uuid
from dataclasses import dataclass, field
from typing import List, Tuple


@dataclass
class Chunk:
    chunk_id: str
    text: str
    page_number: int
    section_title: str
    chunk_index: int
    document_id: int = field(default=0)


# Markdown headings, normal academic headings, and short uppercase headings.
HEADER_PATTERN = re.compile(
    r"^(#{1,3}\s+.+|"
    r"[A-Z][A-Za-z0-9 ,&()\-]{3,80}:?)$"
)


# Detect common list/bullet formats.
BULLET_PATTERN = re.compile(
    r"^\s*(?:"
    r"[•●▪◦‣⁃*-]\s+|"
    r"\d+[.)]\s+|"
    r"[A-Za-z][.)]\s+"
    r")"
)


def _detect_section_title(paragraph: str, current: str) -> str:
    """
    Detect a likely section heading.
    """
    first_line = paragraph.strip().splitlines()[0] if paragraph.strip() else ""

    cleaned = first_line.strip()

    if (
        HEADER_PATTERN.match(cleaned)
        and len(cleaned) < 100
        and not BULLET_PATTERN.match(cleaned)
    ):
        return cleaned.strip("# ").strip()

    return current


def _normalize_text(text: str) -> str:
    """
    Normalize extracted PDF text while preserving useful line structure.
    """
    text = text.replace("\r\n", "\n").replace("\r", "\n")

    # Normalize unusual spaces.
    text = text.replace("\u00a0", " ")

    # Remove excessive spaces.
    text = re.sub(r"[ \t]+", " ", text)

    # Remove excessive blank lines.
    text = re.sub(r"\n{3,}", "\n\n", text)

    return text.strip()


def _split_into_blocks(text: str) -> List[str]:
    """
    Split page text into logical blocks.

    Priority:
    1. Blank-line paragraphs.
    2. Bullet/list items.
    3. Continuation lines belonging to the previous block.

    This prevents a list item such as:
        Feature extraction: ...
    from being cut arbitrarily.
    """

    text = _normalize_text(text)

    if not text:
        return []

    lines = [line.strip() for line in text.split("\n")]

    blocks: List[str] = []
    current_lines: List[str] = []

    def flush():
        nonlocal current_lines

        if current_lines:
            block = " ".join(
                line.strip()
                for line in current_lines
                if line.strip()
            ).strip()

            if block:
                blocks.append(block)

            current_lines = []

    for line in lines:

        if not line:
            flush()
            continue

        is_bullet = bool(BULLET_PATTERN.match(line))

        if is_bullet and current_lines:
            # New bullet starts a new logical block.
            flush()

        current_lines.append(line)

    flush()

    return blocks


def _split_long_block(text: str, max_size: int) -> List[str]:
    """
    Split a single oversized block using sentence boundaries.

    We only fall back to character slicing if one sentence itself
    is larger than max_size.
    """

    if len(text) <= max_size:
        return [text]

    sentences = re.split(
        r"(?<=[.!?])\s+",
        text
    )

    pieces: List[str] = []
    current = ""

    for sentence in sentences:

        sentence = sentence.strip()

        if not sentence:
            continue

        candidate = (
            sentence
            if not current
            else current + " " + sentence
        )

        if len(candidate) <= max_size:
            current = candidate
        else:
            if current:
                pieces.append(current)

            # Extremely long sentence fallback.
            if len(sentence) > max_size:
                start = 0

                while start < len(sentence):
                    end = min(start + max_size, len(sentence))
                    pieces.append(sentence[start:end].strip())
                    start = end

                current = ""
            else:
                current = sentence

    if current:
        pieces.append(current)

    return pieces


def _build_chunks_from_blocks(
    blocks: List[str],
    page_number: int,
    section_title: str,
    chunk_index_start: int,
    chunk_size: int,
    overlap_blocks: int,
) -> Tuple[List[Chunk], int]:

    chunks: List[Chunk] = []

    current_blocks: List[str] = []
    current_length = 0
    chunk_index = chunk_index_start

    def emit(block_list: List[str]):
        nonlocal chunk_index

        if not block_list:
            return

        text = "\n\n".join(block_list).strip()

        if not text:
            return

        chunks.append(
            Chunk(
                chunk_id=str(uuid.uuid4()),
                text=text,
                page_number=page_number,
                section_title=section_title,
                chunk_index=chunk_index,
            )
        )

        chunk_index += 1

    for block in blocks:

        # If a single logical block is too large,
        # split it safely using sentence boundaries.
        block_parts = _split_long_block(
            block,
            chunk_size
        )

        for part in block_parts:

            additional_length = (
                len(part)
                if not current_blocks
                else len(part) + 2
            )

            if (
                current_blocks
                and current_length + additional_length > chunk_size
            ):
                emit(current_blocks)

                # Logical overlap:
                # carry the last complete block(s).
                overlap = current_blocks[
                    -overlap_blocks:
                ]

                current_blocks = overlap.copy()

                current_length = sum(
                    len(x) for x in current_blocks
                )

                if current_blocks:
                    current_length += (
                        2 * (len(current_blocks) - 1)
                    )

            current_blocks.append(part)

            current_length += (
                len(part)
                if len(current_blocks) == 1
                else len(part) + 2
            )

    if current_blocks:
        emit(current_blocks)

    return chunks, chunk_index


def chunk_pages(
    pages: List[Tuple[str, int]],
    chunk_size: int = 1600,
    overlap: int = 1,
) -> List[Chunk]:
    """
    Convert pages into metadata-aware chunks.

    Default:
        chunk_size = 1600 characters
        overlap = 1 complete logical block

    Important:
    We preserve page boundaries so citations remain accurate.
    """

    chunks: List[Chunk] = []

    chunk_index = 0
    current_section = "Introduction"

    for text, page_number in pages:

        normalized = _normalize_text(text)

        if not normalized:
            continue

        blocks = _split_into_blocks(normalized)

        if not blocks:
            continue

        # Detect section headings before chunk construction.
        enriched_blocks: List[Tuple[str, str]] = []

        for block in blocks:
            current_section = _detect_section_title(
                block,
                current_section
            )

            enriched_blocks.append(
                (block, current_section)
            )

        # Group consecutive blocks belonging to the same section.
        section_groups: List[Tuple[str, List[str]]] = []

        for block, section in enriched_blocks:

            if (
                section_groups
                and section_groups[-1][0] == section
            ):
                section_groups[-1][1].append(block)
            else:
                section_groups.append(
                    (section, [block])
                )

        for section_title, section_blocks in section_groups:

            new_chunks, chunk_index = _build_chunks_from_blocks(
                blocks=section_blocks,
                page_number=page_number,
                section_title=section_title,
                chunk_index_start=chunk_index,
                chunk_size=chunk_size,
                overlap_blocks=overlap,
            )

            chunks.extend(new_chunks)

    return chunks
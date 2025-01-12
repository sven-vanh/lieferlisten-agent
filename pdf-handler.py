# Import dependencies
import fitz  # PyMuPDF
import sys
import re
import logging

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# Function to get the PDF object safely
def read_pdf(file_path: str, encoding: str = 'utf-8') -> fitz.Document:
    """Read a PDF file and return the PDF object

    Args:
        file_path (str): Path to the PDF file
        encoding (str): PDF text encoding. Supported values:
            - 'utf-8' (default)
            - 'latin1' (iso-8859-1)
            - 'ascii'
            - 'utf-16'
            - 'utf-32'

    Returns:
        fitz.Document: PDF object
    """
    try:
        pdf = fitz.open(file_path)
        pdf.set_metadata({'encoding': encoding})
        return pdf
    except Exception as e:
        print(f"Error reading PDF {file_path}: {e}")
        sys.exit(1)


# Function to split the PDF by "M" followed by numbers with a buffer
def split_into_sections(pdf: fitz.Document) -> list:
    """Split the PDF by "M" followed by numbers with a buffer
    
    Args:
        pdf (fitz.Document): PDF object
    
    Returns:
        list: List of sections based on "M" patterns
    """
    sections = []
    pattern = re.compile(r"M\d+")
    for page_num, page in enumerate(pdf):
        blocks_on_page = page.get_text("dict")["blocks"]
        for block in blocks_on_page:
            if block['type'] == 0:  # text block
                for line in block['lines']:
                    for span in line['spans']:
                        if pattern.match(span['text']):
                            buffered_y = span['bbox'][1] + 10  # Add 10px buffer
                            sections.append({
                                'page_num': page_num,
                                'text': span['text'].strip(),
                                'bbox_top': buffered_y
                            })
    logging.info(f"Found {len(sections)} sections in the PDF.")
    return sections


# Function to compare text blocks
def compare_text_blocks(source_blocks: list, target_blocks: list) -> list:
    """Compare text blocks from source and target PDFs

    Args:
        source_blocks (list): List of blocks from the source PDF
        target_blocks (list): List of blocks from the target PDF

    Returns:
        list: List of matching blocks
    """
    matches = []
    source_texts = {b['text']: b for b in source_blocks}
    for t_block in target_blocks:
        if t_block['text'] in source_texts:
            matches.append((source_texts[t_block['text']], t_block))
    match_percentage = (len(matches) / len(target_blocks)) * 100 if target_blocks else 0
    logging.info(f"Found {len(matches)} matching blocks out of {len(target_blocks)} target blocks ({match_percentage:.2f}%).")
    return matches


# Function to extract comments from a block
def extract_comments(pdf: fitz.Document, block: dict) -> list:
    """Extract comments from a block

    Args:
        pdf (fitz.Document): PDF object
        block (dict): Block containing the text

    Returns:
        list: List of comments
    """
    comments = []
    page = pdf[block['page_num']]
    annot = page.first_annot
    while annot:
        annot_bbox = annot.rect
        if block['bbox'][1] <= annot_bbox.y0 <= block['bbox'][3]:
            comments.append({
                'content': annot.info.get("content", ""),
                'rect': annot_bbox
            })
        annot = annot.next
    return comments


# Function to copy comments to a target block
def copy_comments(comments, target_page, target_block):
    logging.info(f"Adding {len(comments)} comments to page {target_page.number}.")
    for comment in comments:
        new_rect = fitz.Rect(
            comment['rect'].x0,
            target_block['bbox'][1],
            comment['rect'].x1,
            target_block['bbox'][3]
        )
        target_page.add_text_annot(new_rect, comment['content'])


# Wrapper function to annotate the whole PDF
def annotate_pdf(source_pdf_path: str, target_pdf_path: str, output_pdf_path: str, encoding: str = 'utf-8') -> None:
    """Annotate the target PDF with comments from the source PDF

    Args:
        source_pdf_path (str): The path to the source PDF
        target_pdf_path (str): The path to the target PDF
        output_pdf_path (str): The path to save the annotated PDF
        encoding (str): PDF text encoding (default: 'utf-8')
    """
    # Read the PDFs
    source_pdf = read_pdf(source_pdf_path, encoding)
    target_pdf = read_pdf(target_pdf_path, encoding)

    # Split the PDFs by bold text
    source_blocks = split_into_sections(source_pdf)
    target_blocks = split_into_sections(target_pdf)

    # Compare the text blocks
    matches = compare_text_blocks(source_blocks, target_blocks)

    # Annotate the target PDF
    for s_block, t_block in matches:
        comments = extract_comments(source_pdf, s_block)
        target_page = target_pdf[t_block['page_num']]
        copy_comments(comments, target_page, t_block)

    # Save the annotated PDF
    try:
        target_pdf.save(output_pdf_path)
        logging.info(f"Annotated PDF saved to {output_pdf_path}")
    # Error handling for the PDF saving
    except Exception as e:
        print(f"Error saving PDF: {e}")


# Main function
if __name__ == "__main__":
    # Check if the arguments are provided
    if len(sys.argv) != 4:
        print("Usage: python pdf-handler.py source.pdf target.pdf output.pdf")
        sys.exit(1)
    # Extract CLI arguments
    source_pdf_path = sys.argv[1]
    target_pdf_path = sys.argv[2]
    output_pdf_path = sys.argv[3]

    logging.info("Starting PDF annotation process.")
    # Annotate the PDF
    annotate_pdf(source_pdf_path, target_pdf_path, output_pdf_path)
    logging.info("PDF annotation process completed.")

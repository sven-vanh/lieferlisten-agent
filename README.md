# PDF Comment Transfer Tool

A Python tool that transfers comments/annotations from one PDF to another by matching bold text sections.

## Features

- Identifies and matches bold text sections between two PDFs
- Copies annotations/comments from the source PDF to the target PDF
- Preserves the vertical positioning of annotations
- Handles multiple pages and multiple annotations

## Requirements

- Python 3.x
- PyMuPDF (fitz)

To install the required package:
```bash
pip install PyMuPDF
```

## Usage

Run the script from the command line with three arguments:

```bash
python pdf-handler.py source.pdf target.pdf output.pdf
```

Where:
- `source.pdf`: The PDF containing the original comments/annotations
- `target.pdf`: The PDF where you want to copy the comments to
- `output.pdf`: The path where the newly annotated PDF will be saved

## How It Works

1. The tool reads both source and target PDFs
2. Identifies bold text sections in both documents
3. Matches corresponding sections based on text content and page number
4. Extracts comments from the source PDF's matched sections
5. Creates new annotations in the target PDF at corresponding positions
6. Saves the annotated PDF to the specified output path

## Error Handling

The tool includes error handling for:
- PDF file reading/opening
- Invalid command-line arguments
- PDF saving operations

## Limitations

- Matching is based on exact text matches and page numbers
- Only works with text annotations
- Requires bold text sections to be present in both PDFs

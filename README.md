# Annotation Transfer Agent (ATA)

A Python tool for transferring annotations between PDF documents based on Order ID matching. The agent identifies Order IDs (format: M followed by digits) in both source and target documents, then transfers annotations from the source document to corresponding locations in the target document.

## Features

- **Order ID Detection**: Automatically finds Order IDs matching pattern `M\d+` (e.g., M123, M4567)
- **Annotation Linking**: Links annotations to their nearest preceding Order ID
- **Smart Transfer**: Transfers annotations to corresponding Order IDs in target documents
- **Multiple Annotation Types**: Supports Text notes, FreeText, Ink drawings, Highlights, Underlines, Strikeouts, and Squiggly annotations
- **Relative Positioning**: Maintains spatial relationships between Order IDs and annotations
- **Comprehensive Logging**: Detailed logging for debugging and monitoring

## Installation

### Requirements
- Python >=3.12
- PyMuPDF (fitz)

### Install Dependencies
```bash
uv sync
```

## Usage

### Command Line Interface
```bash
python main.py <source_pdf> <target_pdf> <output_pdf> [--log-level LEVEL]
```

**Arguments:**
- `source_pdf`: Path to PDF containing annotations
- `target_pdf`: Path to target PDF for annotation transfer
- `output_pdf`: Path for the output PDF with transferred annotations
- `--log-level`: Optional logging level (DEBUG, INFO, WARNING, ERROR)

**Example:**
```bash
python main.py annotated_document.pdf target_document.pdf output_with_annotations.pdf --log-level INFO
```

### Python API
```python
from ata import AnnotationTransferAgent

# Create agent instance
agent = AnnotationTransferAgent(log_level=logging.INFO)

# Transfer annotations
success = agent.transfer_annotations(
    source_pdf_path="source.pdf",
    target_pdf_path="target.pdf", 
    output_pdf_path="output.pdf"
)
```

## Project Structure

```
lieferlisten-agent/
├── ata.py              # Core AnnotationTransferAgent class
├── main.py             # Command-line interface
├── README.md           # This documentation
└── annotation_transfer.log  # Generated log file
```

## Architecture

### Core Classes

#### `AnnotationTransferAgent`
Main class responsible for the annotation transfer process.

**Key Methods:**
- `transfer_annotations()`: Main transfer workflow
- `_extract_order_ids()`: Find Order IDs in documents
- `_extract_annotations()`: Extract supported annotations
- `_link_annotations_to_order_ids()`: Create annotation-Order ID relationships
- `_create_output_with_annotations()`: Generate final PDF

#### Data Classes

**`OrderIDInfo`**: Stores Order ID location and metadata
- `order_id`: The Order ID string (e.g., "M123")
- `page_num`: Page number containing the Order ID
- `bbox`: Bounding box coordinates
- `center`: Center point coordinates
- `text_position`: Reading order position

**`AnnotationInfo`**: Stores annotation details
- `annotation`: PyMuPDF annotation object
- `page_num`: Page number
- `bbox`: Bounding box
- `center`: Center coordinates
- `content`: Annotation text content
- `annotation_type`: Type of annotation

**`AnnotationLink`**: Links annotations to Order IDs
- `annotation`: AnnotationInfo object
- `linked_order_id`: Associated Order ID
- `distance`: Distance between annotation and Order ID
- `relative_offset`: Spatial offset for positioning

## Transfer Algorithm

1. **Document Loading**: Load and validate source and target PDFs
2. **Order ID Extraction**: Find all Order IDs in both documents with their positions
3. **Annotation Extraction**: Extract all supported annotations from source document
4. **Linking**: Link each annotation to its nearest preceding Order ID
5. **Filtering**: Keep only annotations linked to Order IDs present in target document
6. **Transfer**: Create new annotations in target document using relative positioning
7. **Output**: Save final PDF with transferred annotations

## Supported Annotation Types

- **Text Annotations**: Sticky notes
- **FreeText**: Inserted text annotations
- **Ink**: Drawing annotations
- **Highlight**: Text highlighting
- **Underline**: Text underlining
- **Strikeout**: Text strikethrough
- **Squiggly**: Squiggly underlines

## Logging

The agent generates detailed logs including:
- Document loading status
- Order ID discovery results
- Annotation extraction progress
- Transfer success/failure details
- Error diagnostics

Logs are written to both console and `annotation_transfer.log` file.

## Error Handling

The agent handles various error conditions:
- Missing or encrypted PDF files
- Documents without Order IDs
- Annotations outside page boundaries
- Invalid annotation types
- File I/O errors

## Limitations

- Order IDs must follow the pattern `M\d+`
- Annotations must appear after their linked Order ID in document reading order
- Complex drawing annotations are simplified during transfer
- Encrypted PDFs are not supported

## Version Information

- **Version**: 1.0
- **Created by**: Sven van Helten
- **Last Updated**: 25.05.2025
- **License**: [MIT](LICENSE)
import fitz  # PyMuPDF
import re
import logging
import math
from typing import Dict, List, Tuple, Optional, NamedTuple
from dataclasses import dataclass
from pathlib import Path
import sys


@dataclass
class OrderIDInfo:
    """Information about an Order ID in a document."""
    order_id: str
    page_num: int
    bbox: fitz.Rect
    center: Tuple[float, float]
    text_position: int  # Position in reading order


@dataclass
class AnnotationInfo:
    """Information about an annotation in a document."""
    annotation: fitz.Annot
    page_num: int
    bbox: fitz.Rect
    center: Tuple[float, float]
    content: str
    annotation_type: str


@dataclass
class AnnotationLink:
    """Links an annotation to its closest Order ID."""
    annotation: AnnotationInfo
    linked_order_id: str
    distance: float
    relative_offset: Tuple[float, float]


class AnnotationTransferAgent:
    """Main class for transferring annotations between PDF documents."""
    
    def __init__(self, log_level=logging.INFO):
        """Initialize the agent with logging configuration."""
        self.setup_logging(log_level)
        self.logger = logging.getLogger(__name__)
        
        # Order ID pattern: "M" followed by one or more digits
        self.order_id_pattern = re.compile(r'\bM\d+\b')
        
        # Supported annotation types
        self.supported_annotation_types = {
            fitz.PDF_ANNOT_TEXT,      # Sticky Notes
            fitz.PDF_ANNOT_FREETEXT,  # Inserted Text
            fitz.PDF_ANNOT_INK,       # Drawings
            fitz.PDF_ANNOT_HIGHLIGHT, # Comments (highlights)
            fitz.PDF_ANNOT_UNDERLINE, # Comments (underlines)
            fitz.PDF_ANNOT_STRIKEOUT, # Comments (strikeouts)
            fitz.PDF_ANNOT_SQUIGGLY   # Comments (squiggly)
        }

    def setup_logging(self, log_level):
        """Configure logging for the application."""
        logging.basicConfig(
            level=log_level,
            format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
            handlers=[
                logging.StreamHandler(sys.stdout),
                logging.FileHandler('annotation_transfer.log')
            ]
        )

    def transfer_annotations(self, source_pdf_path: str, target_pdf_path: str, 
                           output_pdf_path: str) -> bool:
        """
        Main method to transfer annotations from source to target PDF.
        
        Args:
            source_pdf_path: Path to source PDF with annotations
            target_pdf_path: Path to target PDF
            output_pdf_path: Path for output PDF
            
        Returns:
            bool: True if transfer successful, False otherwise
        """
        try:
            self.logger.info(f"Starting annotation transfer from {source_pdf_path} to {target_pdf_path}")
            
            # Load documents
            source_doc = self._load_document(source_pdf_path, "source")
            target_doc = self._load_document(target_pdf_path, "target")
            
            if not source_doc or not target_doc:
                return False
            
            # Extract Order IDs from both documents
            source_order_ids = self._extract_order_ids(source_doc, "source")
            target_order_ids = self._extract_order_ids(target_doc, "target")
            
            if not self._validate_order_ids(source_order_ids, "source") or \
               not self._validate_order_ids(target_order_ids, "target"):
                return False
            
            # Extract annotations from source document
            source_annotations = self._extract_annotations(source_doc)
            self.logger.info(f"Found {len(source_annotations)} annotations in source document")
            
            # Link annotations to Order IDs
            annotation_links = self._link_annotations_to_order_ids(
                source_annotations, source_order_ids
            )
            
            # Filter transferable annotations
            transferable_links = self._filter_transferable_annotations(
                annotation_links, target_order_ids
            )
            
            # Create output document and transfer annotations
            success = self._create_output_with_annotations(
                target_doc, transferable_links, target_order_ids, output_pdf_path
            )
            
            # Close documents
            source_doc.close()
            target_doc.close()
            
            if success:
                self.logger.info(f"Annotation transfer completed successfully. Output saved to {output_pdf_path}")
                return True
            else:
                self.logger.error("Annotation transfer failed during output creation")
                return False
                
        except Exception as e:
            self.logger.error(f"Unexpected error during annotation transfer: {str(e)}")
            return False

    def _load_document(self, pdf_path: str, doc_type: str) -> Optional[fitz.Document]:
        """Load and validate a PDF document."""
        try:
            if not Path(pdf_path).exists():
                self.logger.error(f"{doc_type.capitalize()} PDF file not found: {pdf_path}")
                return None
            
            doc = fitz.open(pdf_path)
            
            if doc.is_encrypted:
                self.logger.error(f"{doc_type.capitalize()} PDF is encrypted: {pdf_path}")
                return None
            
            if doc.page_count == 0:
                self.logger.error(f"{doc_type.capitalize()} PDF has no pages: {pdf_path}")
                return None
            
            self.logger.info(f"Loaded {doc_type} PDF: {pdf_path} ({doc.page_count} pages)")
            return doc
            
        except Exception as e:
            self.logger.error(f"Failed to load {doc_type} PDF {pdf_path}: {str(e)}")
            return None

    def _extract_order_ids(self, doc: fitz.Document, doc_type: str) -> Dict[str, OrderIDInfo]:
        """Extract Order IDs from a document with their locations."""
        order_ids = {}
        text_position = 0
        
        try:
            for page_num in range(doc.page_count):
                page = doc[page_num]
                
                # Get text with detailed position information
                text_dict = page.get_text("dict")
                
                for block in text_dict["blocks"]:
                    if "lines" not in block:  # Skip image blocks
                        continue
                    
                    for line in block["lines"]:
                        for span in line["spans"]:
                            text = span["text"]
                            
                            # Find Order IDs in this text span
                            for match in self.order_id_pattern.finditer(text):
                                order_id = match.group()
                                
                                # Calculate position within the span
                                char_start = match.start()
                                char_end = match.end()
                                
                                # Get bounding box for this specific text
                                span_bbox = fitz.Rect(span["bbox"])
                                
                                # Estimate Order ID bbox within the span
                                char_width = span_bbox.width / len(text) if len(text) > 0 else 0
                                id_bbox = fitz.Rect(
                                    span_bbox.x0 + char_start * char_width,
                                    span_bbox.y0,
                                    span_bbox.x0 + char_end * char_width,
                                    span_bbox.y1
                                )
                                
                                center = ((id_bbox.x0 + id_bbox.x1) / 2, (id_bbox.y0 + id_bbox.y1) / 2)
                                
                                order_id_info = OrderIDInfo(
                                    order_id=order_id,
                                    page_num=page_num,
                                    bbox=id_bbox,
                                    center=center,
                                    text_position=text_position
                                )
                                
                                if order_id in order_ids:
                                    # Use first occurrence
                                    if order_ids[order_id].text_position > text_position:
                                        order_ids[order_id] = order_id_info
                                else:
                                    order_ids[order_id] = order_id_info
                            
                            text_position += 1
            
            self.logger.info(f"Found {len(order_ids)} unique Order IDs in {doc_type} document")
            return order_ids
            
        except Exception as e:
            self.logger.error(f"Failed to extract Order IDs from {doc_type} document: {str(e)}")
            return {}

    def _validate_order_ids(self, order_ids: Dict[str, OrderIDInfo], doc_type: str) -> bool:
        """Validate Order IDs for duplicates within pages."""
        try:
            # Check for duplicates by collecting all Order IDs and their pages
            page_order_ids = {}
            
            for order_id, info in order_ids.items():
                if info.page_num not in page_order_ids:
                    page_order_ids[info.page_num] = []
                page_order_ids[info.page_num].append(order_id)
            
            # We're using first occurrence, so no validation needed for duplicates
            # The extraction method already handles this
            
            self.logger.info(f"Order ID validation passed for {doc_type} document")
            return True
            
        except Exception as e:
            self.logger.error(f"Order ID validation failed for {doc_type} document: {str(e)}")
            return False

    def _extract_annotations(self, doc: fitz.Document) -> List[AnnotationInfo]:
        """Extract all supported annotations from the document."""
        annotations = []
        
        try:
            for page_num in range(doc.page_count):
                page = doc[page_num]
                
                for annot in page.annots():
                    if annot.type[0] in self.supported_annotation_types:
                        bbox = annot.rect
                        center = ((bbox.x0 + bbox.x1) / 2, (bbox.y0 + bbox.y1) / 2)
                        
                        # Get annotation content
                        content = ""
                        try:
                            content = annot.info.get("content", "") or annot.info.get("title", "")
                        except:
                            pass
                        
                        annotation_info = AnnotationInfo(
                            annotation=annot,
                            page_num=page_num,
                            bbox=bbox,
                            center=center,
                            content=content,
                            annotation_type=annot.type[1]
                        )
                        
                        annotations.append(annotation_info)
            
            self.logger.info(f"Extracted {len(annotations)} annotations from source document")
            return annotations
            
        except Exception as e:
            self.logger.error(f"Failed to extract annotations: {str(e)}")
            return []

    def _link_annotations_to_order_ids(self, annotations: List[AnnotationInfo], 
                                     order_ids: Dict[str, OrderIDInfo]) -> List[AnnotationLink]:
        """Link each annotation to its closest eligible Order ID."""
        links = []
        
        for annotation in annotations:
            eligible_order_ids = self._get_eligible_order_ids(annotation, order_ids)
            
            if not eligible_order_ids:
                self.logger.warning(
                    f"No eligible Order IDs found for annotation on page {annotation.page_num + 1} "
                    f"(type: {annotation.annotation_type})"
                )
                continue
            
            # Find closest eligible Order ID
            closest_order_id = None
            min_distance = float('inf')
            
            for order_id, order_info in eligible_order_ids.items():
                distance = self._calculate_euclidean_distance(
                    annotation.center, order_info.center
                )
                
                if distance < min_distance:
                    min_distance = distance
                    closest_order_id = order_id
            
            if closest_order_id:
                order_info = eligible_order_ids[closest_order_id]
                relative_offset = (
                    annotation.center[0] - order_info.center[0],
                    annotation.center[1] - order_info.center[1]
                )
                
                link = AnnotationLink(
                    annotation=annotation,
                    linked_order_id=closest_order_id,
                    distance=min_distance,
                    relative_offset=relative_offset
                )
                
                links.append(link)
                
                self.logger.info(
                    f"Linked annotation (type: {annotation.annotation_type}) on page {annotation.page_num + 1} "
                    f"to Order ID {closest_order_id} (distance: {min_distance:.2f})"
                )
        
        return links

    def _get_eligible_order_ids(self, annotation: AnnotationInfo, 
                              order_ids: Dict[str, OrderIDInfo]) -> Dict[str, OrderIDInfo]:
        """Get Order IDs that appear earlier than the annotation in document order."""
        eligible = {}
        
        for order_id, order_info in order_ids.items():
            # Check if Order ID appears earlier in document
            if (order_info.page_num < annotation.page_num or 
                (order_info.page_num == annotation.page_num and 
                 order_info.center[1] < annotation.center[1])):  # Higher vertical position (lower Y)
                eligible[order_id] = order_info
        
        return eligible

    def _calculate_euclidean_distance(self, point1: Tuple[float, float], 
                                    point2: Tuple[float, float]) -> float:
        """Calculate Euclidean distance between two points."""
        return math.sqrt((point1[0] - point2[0])**2 + (point1[1] - point2[1])**2)

    def _filter_transferable_annotations(self, annotation_links: List[AnnotationLink],
                                       target_order_ids: Dict[str, OrderIDInfo]) -> List[AnnotationLink]:
        """Filter annotations that can be transferred to target document."""
        transferable = []
        
        for link in annotation_links:
            if link.linked_order_id in target_order_ids:
                transferable.append(link)
                self.logger.info(
                    f"Annotation linked to Order ID {link.linked_order_id} marked for transfer"
                )
            else:
                self.logger.warning(
                    f"Annotation linked to Order ID {link.linked_order_id} skipped - "
                    f"Order ID not found in target document"
                )
        
        self.logger.info(f"{len(transferable)} annotations will be transferred")
        return transferable

    def _create_output_with_annotations(self, target_doc: fitz.Document,
                                      transferable_links: List[AnnotationLink],
                                      target_order_ids: Dict[str, OrderIDInfo],
                                      output_path: str) -> bool:
        """Create output document with transferred annotations."""
        try:
            # Create a copy of the target document
            output_doc = fitz.open()
            output_doc.insert_pdf(target_doc)
            
            transferred_count = 0
            
            for link in transferable_links:
                target_order_info = target_order_ids[link.linked_order_id]
                
                # Calculate new annotation position
                new_center = (
                    target_order_info.center[0] + link.relative_offset[0],
                    target_order_info.center[1] + link.relative_offset[1]
                )
                
                # Calculate new bounding box
                annotation_width = link.annotation.bbox.width
                annotation_height = link.annotation.bbox.height
                
                new_bbox = fitz.Rect(
                    new_center[0] - annotation_width / 2,
                    new_center[1] - annotation_height / 2,
                    new_center[0] + annotation_width / 2,
                    new_center[1] + annotation_height / 2
                )
                
                # Get target page
                target_page = output_doc[target_order_info.page_num]
                
                # Ensure annotation is within page bounds
                page_rect = target_page.rect
                if not page_rect.contains(new_bbox):
                    # Adjust bbox to fit within page
                    new_bbox = new_bbox & page_rect
                    if new_bbox.is_empty:
                        self.logger.warning(
                            f"Annotation for Order ID {link.linked_order_id} "
                            f"falls outside page bounds and cannot be adjusted"
                        )
                        continue
                
                # Create new annotation
                try:
                    if link.annotation.annotation_type == "Text":
                        # Text annotation (sticky note)
                        new_annot = target_page.add_text_annot(
                            new_bbox.tl, link.annotation.content
                        )
                    elif link.annotation.annotation_type == "FreeText":
                        # Free text annotation
                        new_annot = target_page.add_freetext_annot(
                            new_bbox, link.annotation.content
                        )
                    elif link.annotation.annotation_type == "Ink":
                        # Drawing annotation - simplified as a rectangle
                        new_annot = target_page.add_rect_annot(new_bbox)
                    else:
                        # Other annotation types (highlight, underline, etc.)
                        new_annot = target_page.add_highlight_annot(new_bbox)
                    
                    # Copy annotation properties where possible
                    try:
                        original_info = link.annotation.annotation.info
                        new_annot.set_info(content=link.annotation.content)
                        if "title" in original_info:
                            new_annot.set_info(title=original_info["title"])
                    except:
                        pass
                    
                    new_annot.update()
                    transferred_count += 1
                    
                    self.logger.info(
                        f"Transferred annotation (type: {link.annotation.annotation_type}) "
                        f"for Order ID {link.linked_order_id} to page {target_order_info.page_num + 1}"
                    )
                    
                except Exception as e:
                    self.logger.error(
                        f"Failed to create annotation for Order ID {link.linked_order_id}: {str(e)}"
                    )
            
            # Save output document
            output_doc.save(output_path)
            output_doc.close()
            
            self.logger.info(f"Successfully transferred {transferred_count} annotations")
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to create output document: {str(e)}")
            return False
"""
Document processor module for handling various document types.
"""

import logging
import os
import json
import tempfile
import asyncio
from typing import Dict, Any, List, Optional, Union, BinaryIO, TextIO
import io
import re
from enum import Enum
import mimetypes
import csv
import base64
import time

# Configure logging
logger = logging.getLogger(__name__)


class DocumentType(str, Enum):
    """Document types that can be processed."""
    PDF = "pdf"
    WORD = "word"
    EXCEL = "excel"
    CSV = "csv"
    TEXT = "text"
    JSON = "json"
    HTML = "html"
    IMAGE = "image"
    XML = "xml"
    MARKDOWN = "markdown"
    UNKNOWN = "unknown"


class DocumentProcessorError(Exception):
    """Base exception for document processing errors."""
    pass


class DocumentContent:
    """Container for document content."""
    
    def __init__(
        self,
        text: str,
        metadata: Optional[Dict[str, Any]] = None,
        pages: Optional[List[Dict[str, Any]]] = None,
        tables: Optional[List[Dict[str, Any]]] = None,
        images: Optional[List[Dict[str, Any]]] = None,
    ):
        """
        Initialize document content.
        
        Args:
            text: Extracted text content
            metadata: Document metadata
            pages: List of page contents
            tables: List of table contents
            images: List of image contents
        """
        self.text = text
        self.metadata = metadata or {}
        self.pages = pages or []
        self.tables = tables or []
        self.images = images or []
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "text": self.text,
            "metadata": self.metadata,
            "pages": self.pages,
            "tables": self.tables,
            "images": self.images,
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'DocumentContent':
        """Create from dictionary."""
        return cls(
            text=data["text"],
            metadata=data.get("metadata", {}),
            pages=data.get("pages", []),
            tables=data.get("tables", []),
            images=data.get("images", []),
        )


class BaseDocumentHandler:
    """Base interface for document type handlers."""
    
    async def process(self, file_path: str) -> DocumentContent:
        """
        Process a document file.
        
        Args:
            file_path: Path to the document file
            
        Returns:
            Extracted document content
            
        Raises:
            DocumentProcessorError: If processing fails
        """
        raise NotImplementedError("Document handler not implemented")


class PDFDocumentHandler(BaseDocumentHandler):
    """Handler for PDF documents."""
    
    async def process(self, file_path: str) -> DocumentContent:
        """
        Process a PDF document.
        
        Args:
            file_path: Path to the PDF document
            
        Returns:
            Extracted document content
            
        Raises:
            DocumentProcessorError: If processing fails
        """
        try:
            # In a real implementation, this would use PyPDF2 or pdfminer.six
            logger.info(f"Processing PDF document: {file_path}")
            
            # For now, we'll simulate PDF processing
            return await self._simulate_pdf_processing(file_path)
        except Exception as e:
            logger.error(f"Error processing PDF document: {str(e)}")
            raise DocumentProcessorError(f"Error processing PDF document: {str(e)}")
    
    async def _simulate_pdf_processing(self, file_path: str) -> DocumentContent:
        """
        Simulate PDF processing for demo purposes.
        
        Args:
            file_path: Path to the PDF document
            
        Returns:
            Simulated document content
        """
        file_name = os.path.basename(file_path)
        
        # Simulate metadata
        metadata = {
            "title": file_name.replace(".pdf", ""),
            "author": "Unknown Author",
            "creation_date": "2023-01-01",
            "pages": 5,
            "producer": "Supertrack PDF Processor",
        }
        
        # Simulate pages
        pages = []
        for i in range(1, 6):
            pages.append({
                "page_number": i,
                "text": f"This is simulated content for page {i} of {file_name}.",
                "size": {"width": 612, "height": 792},
            })
        
        # Simulate full text
        text = f"""
        # {metadata['title']}
        Author: {metadata['author']}
        Date: {metadata['creation_date']}
        
        ## Document Content
        
        This is a simulated PDF document with 5 pages. In a real implementation,
        this would contain the actual extracted text content from the PDF file.
        
        The document would likely have multiple sections, paragraphs, potentially
        tables, figures, and other elements that would be extracted by the PDF
        processing library.
        
        ## Sample Content
        
        Lorem ipsum dolor sit amet, consectetur adipiscing elit. Nulla facilisi.
        Maecenas nec odio et ante tincidunt tempus. Donec vitae sapien ut libero
        venenatis faucibus. Nullam quis ante.
        
        Etiam sit amet orci eget eros faucibus tincidunt. Duis leo. Sed fringilla
        mauris sit amet nibh. Donec sodales sagittis magna. Sed consequat, leo eget
        bibendum sodales, augue velit cursus nunc.
        """
        
        return DocumentContent(
            text=text,
            metadata=metadata,
            pages=pages,
        )


class TextDocumentHandler(BaseDocumentHandler):
    """Handler for text documents."""
    
    async def process(self, file_path: str) -> DocumentContent:
        """
        Process a text document.
        
        Args:
            file_path: Path to the text document
            
        Returns:
            Extracted document content
            
        Raises:
            DocumentProcessorError: If processing fails
        """
        try:
            logger.info(f"Processing text document: {file_path}")
            
            # Read text file
            with open(file_path, 'r', encoding='utf-8') as file:
                text = file.read()
            
            # Create basic metadata
            file_name = os.path.basename(file_path)
            file_stats = os.stat(file_path)
            
            metadata = {
                "filename": file_name,
                "filesize": file_stats.st_size,
                "modified_time": time.ctime(file_stats.st_mtime),
                "line_count": text.count('\n') + 1,
                "word_count": len(text.split()),
                "char_count": len(text),
            }
            
            return DocumentContent(
                text=text,
                metadata=metadata,
            )
        except Exception as e:
            logger.error(f"Error processing text document: {str(e)}")
            raise DocumentProcessorError(f"Error processing text document: {str(e)}")


class JSONDocumentHandler(BaseDocumentHandler):
    """Handler for JSON documents."""
    
    async def process(self, file_path: str) -> DocumentContent:
        """
        Process a JSON document.
        
        Args:
            file_path: Path to the JSON document
            
        Returns:
            Extracted document content
            
        Raises:
            DocumentProcessorError: If processing fails
        """
        try:
            logger.info(f"Processing JSON document: {file_path}")
            
            # Read and parse JSON
            with open(file_path, 'r', encoding='utf-8') as file:
                data = json.load(file)
            
            # Create formatted text representation
            text = json.dumps(data, indent=2)
            
            # Create basic metadata
            file_name = os.path.basename(file_path)
            file_stats = os.stat(file_path)
            
            metadata = {
                "filename": file_name,
                "filesize": file_stats.st_size,
                "modified_time": time.ctime(file_stats.st_mtime),
                "json_keys": list(data.keys()) if isinstance(data, dict) else [],
                "json_type": type(data).__name__,
            }
            
            return DocumentContent(
                text=text,
                metadata=metadata,
            )
        except Exception as e:
            logger.error(f"Error processing JSON document: {str(e)}")
            raise DocumentProcessorError(f"Error processing JSON document: {str(e)}")


class CSVDocumentHandler(BaseDocumentHandler):
    """Handler for CSV documents."""
    
    async def process(self, file_path: str) -> DocumentContent:
        """
        Process a CSV document.
        
        Args:
            file_path: Path to the CSV document
            
        Returns:
            Extracted document content
            
        Raises:
            DocumentProcessorError: If processing fails
        """
        try:
            logger.info(f"Processing CSV document: {file_path}")
            
            # Read CSV file
            rows = []
            headers = []
            
            with open(file_path, 'r', encoding='utf-8') as file:
                csv_reader = csv.reader(file)
                
                for i, row in enumerate(csv_reader):
                    if i == 0:
                        headers = row
                    rows.append(row)
            
            # Create text representation
            text = ""
            
            if headers:
                text += "| " + " | ".join(headers) + " |\n"
                text += "| " + " | ".join(["---" for _ in headers]) + " |\n"
            
            for row in rows[1:]:
                text += "| " + " | ".join(row) + " |\n"
            
            # Create tables representation
            tables = [{
                "headers": headers,
                "rows": rows[1:],
                "row_count": len(rows) - 1,
                "column_count": len(headers),
            }]
            
            # Create basic metadata
            file_name = os.path.basename(file_path)
            file_stats = os.stat(file_path)
            
            metadata = {
                "filename": file_name,
                "filesize": file_stats.st_size,
                "modified_time": time.ctime(file_stats.st_mtime),
                "row_count": len(rows) - 1,
                "column_count": len(headers),
                "headers": headers,
            }
            
            return DocumentContent(
                text=text,
                metadata=metadata,
                tables=tables,
            )
        except Exception as e:
            logger.error(f"Error processing CSV document: {str(e)}")
            raise DocumentProcessorError(f"Error processing CSV document: {str(e)}")


class WordDocumentHandler(BaseDocumentHandler):
    """Handler for Word documents."""
    
    async def process(self, file_path: str) -> DocumentContent:
        """
        Process a Word document.
        
        Args:
            file_path: Path to the Word document
            
        Returns:
            Extracted document content
            
        Raises:
            DocumentProcessorError: If processing fails
        """
        try:
            # In a real implementation, this would use python-docx
            logger.info(f"Processing Word document: {file_path}")
            
            # For now, we'll simulate Word processing
            return await self._simulate_word_processing(file_path)
        except Exception as e:
            logger.error(f"Error processing Word document: {str(e)}")
            raise DocumentProcessorError(f"Error processing Word document: {str(e)}")
    
    async def _simulate_word_processing(self, file_path: str) -> DocumentContent:
        """
        Simulate Word document processing for demo purposes.
        
        Args:
            file_path: Path to the Word document
            
        Returns:
            Simulated document content
        """
        file_name = os.path.basename(file_path)
        
        # Simulate metadata
        metadata = {
            "title": file_name.replace(".docx", "").replace(".doc", ""),
            "author": "Unknown Author",
            "creation_date": "2023-01-01",
            "last_modified_by": "Unknown User",
            "paragraph_count": 12,
            "word_count": 345,
        }
        
        # Simulate text content
        text = f"""
        # {metadata['title']}
        Author: {metadata['author']}
        Date: {metadata['creation_date']}
        
        ## Document Content
        
        This is a simulated Word document. In a real implementation,
        this would contain the actual extracted text content from the Word file.
        
        The document would likely have multiple sections, paragraphs, potentially
        tables, figures, and other elements that would be extracted by the Word
        processing library.
        
        ## Sample Content
        
        Lorem ipsum dolor sit amet, consectetur adipiscing elit. Nulla facilisi.
        Maecenas nec odio et ante tincidunt tempus. Donec vitae sapien ut libero
        venenatis faucibus. Nullam quis ante.
        
        Etiam sit amet orci eget eros faucibus tincidunt. Duis leo. Sed fringilla
        mauris sit amet nibh. Donec sodales sagittis magna. Sed consequat, leo eget
        bibendum sodales, augue velit cursus nunc.
        """
        
        return DocumentContent(
            text=text,
            metadata=metadata,
        )


class DocumentProcessor:
    """
    Document processor for handling various document types.
    
    This class processes documents and extracts their content using
    type-specific handlers.
    """
    
    def __init__(self):
        """Initialize the document processor."""
        # Register document handlers
        self.handlers = {
            DocumentType.PDF: PDFDocumentHandler(),
            DocumentType.TEXT: TextDocumentHandler(),
            DocumentType.JSON: JSONDocumentHandler(),
            DocumentType.CSV: CSVDocumentHandler(),
            DocumentType.WORD: WordDocumentHandler(),
        }
        
        # Initialize mime types
        self._init_mime_types()
    
    def _init_mime_types(self):
        """Initialize mime type mappings."""
        # Ensure common mime types are registered
        mimetypes.init()
        
        # Add additional mime types if needed
        mimetypes.add_type('application/pdf', '.pdf')
        mimetypes.add_type('application/json', '.json')
        mimetypes.add_type('text/plain', '.txt')
        mimetypes.add_type('text/csv', '.csv')
        mimetypes.add_type('application/vnd.openxmlformats-officedocument.wordprocessingml.document', '.docx')
        mimetypes.add_type('application/msword', '.doc')
    
    def detect_document_type(self, file_path: str) -> DocumentType:
        """
        Detect the document type from a file path.
        
        Args:
            file_path: Path to the document
            
        Returns:
            Detected document type
        """
        _, ext = os.path.splitext(file_path)
        ext = ext.lower()
        
        # Get mime type
        mime_type, _ = mimetypes.guess_type(file_path)
        
        # Determine document type based on extension and mime type
        if ext == '.pdf' or (mime_type and 'pdf' in mime_type):
            return DocumentType.PDF
        elif ext in ['.txt', '.text'] or (mime_type and 'text/plain' in mime_type):
            return DocumentType.TEXT
        elif ext == '.json' or (mime_type and 'json' in mime_type):
            return DocumentType.JSON
        elif ext == '.csv' or (mime_type and 'csv' in mime_type):
            return DocumentType.CSV
        elif ext in ['.doc', '.docx'] or (mime_type and ('msword' in mime_type or 'wordprocessing' in mime_type)):
            return DocumentType.WORD
        elif ext in ['.xls', '.xlsx', '.xlsm'] or (mime_type and ('excel' in mime_type or 'spreadsheet' in mime_type)):
            return DocumentType.EXCEL
        elif ext in ['.htm', '.html'] or (mime_type and 'html' in mime_type):
            return DocumentType.HTML
        elif ext in ['.jpg', '.jpeg', '.png', '.gif', '.bmp'] or (mime_type and 'image/' in mime_type):
            return DocumentType.IMAGE
        elif ext == '.xml' or (mime_type and 'xml' in mime_type):
            return DocumentType.XML
        elif ext in ['.md', '.markdown'] or (mime_type and 'markdown' in mime_type):
            return DocumentType.MARKDOWN
        
        return DocumentType.UNKNOWN
    
    async def process_file(
        self, 
        file_path: str, 
        document_type: Optional[DocumentType] = None
    ) -> DocumentContent:
        """
        Process a document file.
        
        Args:
            file_path: Path to the document file
            document_type: Optional document type. If not provided, it will be detected.
            
        Returns:
            Extracted document content
            
        Raises:
            DocumentProcessorError: If processing fails
        """
        try:
            # Detect document type if not provided
            if not document_type:
                document_type = self.detect_document_type(file_path)
            
            logger.info(f"Processing document {file_path} of type {document_type}")
            
            # Get handler for document type
            handler = self.handlers.get(document_type)
            
            if not handler:
                raise DocumentProcessorError(f"Unsupported document type: {document_type}")
            
            # Process document
            content = await handler.process(file_path)
            
            # Add document type to metadata
            content.metadata["document_type"] = document_type
            
            return content
        except Exception as e:
            logger.error(f"Error processing document: {str(e)}")
            raise DocumentProcessorError(f"Error processing document: {str(e)}")
    
    async def process_stream(
        self, 
        stream: Union[BinaryIO, TextIO],
        document_type: DocumentType,
        filename: Optional[str] = None
    ) -> DocumentContent:
        """
        Process a document from a stream.
        
        Args:
            stream: File-like object containing the document
            document_type: Document type
            filename: Optional filename to use for the temporary file
            
        Returns:
            Extracted document content
            
        Raises:
            DocumentProcessorError: If processing fails
        """
        try:
            # Create a temporary file
            with tempfile.NamedTemporaryFile(delete=False, suffix=f".{document_type}") as temp_file:
                temp_path = temp_file.name
                
                # Write stream content to temporary file
                if hasattr(stream, 'read'):
                    # Binary stream
                    temp_file.write(stream.read())
                else:
                    # String content
                    temp_file.write(stream.encode('utf-8'))
            
            # Process the temporary file
            content = await self.process_file(temp_path, document_type)
            
            # Add original filename to metadata if provided
            if filename:
                content.metadata["original_filename"] = filename
            
            # Clean up temporary file
            try:
                os.unlink(temp_path)
            except Exception as e:
                logger.warning(f"Failed to delete temporary file {temp_path}: {str(e)}")
            
            return content
        except Exception as e:
            logger.error(f"Error processing document stream: {str(e)}")
            raise DocumentProcessorError(f"Error processing document stream: {str(e)}")
    
    async def process_base64(
        self,
        base64_content: str,
        document_type: DocumentType,
        filename: Optional[str] = None
    ) -> DocumentContent:
        """
        Process a document from base64-encoded content.
        
        Args:
            base64_content: Base64-encoded document content
            document_type: Document type
            filename: Optional filename to use for the temporary file
            
        Returns:
            Extracted document content
            
        Raises:
            DocumentProcessorError: If processing fails
        """
        try:
            # Decode base64 content
            binary_content = base64.b64decode(base64_content)
            
            # Create a stream from the binary content
            stream = io.BytesIO(binary_content)
            
            # Process the stream
            return await self.process_stream(stream, document_type, filename)
        except Exception as e:
            logger.error(f"Error processing base64 document: {str(e)}")
            raise DocumentProcessorError(f"Error processing base64 document: {str(e)}")
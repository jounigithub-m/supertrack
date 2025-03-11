"""
Document processing package for Supertrack platform.

This package provides functionality for processing various document types
and extracting structured information from them.
"""

from .processor import (
    DocumentType,
    DocumentProcessorError,
    DocumentContent,
    DocumentProcessor,
)

__all__ = [
    'DocumentType',
    'DocumentProcessorError',
    'DocumentContent',
    'DocumentProcessor',
]
#!/usr/bin/env python3
"""
Compression Utilities - Transparent content compression for AI-First tools
Reduces database size by 60-80% for large text fields
"""
import zlib
import lz4.frame
import logging
from typing import Optional, Union
from enum import Enum

class CompressionMethod(Enum):
    """Supported compression methods"""
    ZLIB = "zlib"      # Good compression ratio, moderate speed
    LZ4 = "lz4"        # Fast compression, good for AI responsiveness
    NONE = "none"      # No compression (for small content)

# Compression threshold (don't compress very small content)
MIN_COMPRESSION_SIZE = 200  # bytes

def should_compress(content: str) -> bool:
    """
    Check if content should be compressed

    Args:
        content: Text content to check

    Returns:
        True if content is large enough to benefit from compression
    """
    return len(content.encode('utf-8')) >= MIN_COMPRESSION_SIZE

def compress_content(content: str, method: CompressionMethod = CompressionMethod.LZ4) -> bytes:
    """
    Compress text content transparently

    Args:
        content: Text content to compress
        method: Compression method to use

    Returns:
        Compressed bytes (with method prefix for decompression)

    Format: [method_byte][compressed_data]
    - 0x00 = no compression (raw UTF-8)
    - 0x01 = zlib
    - 0x02 = lz4
    """
    if not content:
        return b'\x00'  # Empty content

    content_bytes = content.encode('utf-8')

    # Skip compression for small content
    if not should_compress(content):
        return b'\x00' + content_bytes

    try:
        if method == CompressionMethod.ZLIB:
            compressed = zlib.compress(content_bytes, level=6)  # Level 6 = good balance
            return b'\x01' + compressed

        elif method == CompressionMethod.LZ4:
            compressed = lz4.frame.compress(content_bytes)
            return b'\x02' + compressed

        else:  # NONE or fallback
            return b'\x00' + content_bytes

    except Exception as e:
        logging.warning(f"[COMPRESS] Compression failed: {e}, storing uncompressed")
        return b'\x00' + content_bytes

def decompress_content(data: Union[bytes, str]) -> str:
    """
    Decompress content transparently

    Args:
        data: Compressed bytes (or raw string for backward compatibility)

    Returns:
        Decompressed text content
    """
    if not data:
        return ""

    # Handle legacy uncompressed strings
    if isinstance(data, str):
        return data

    # Handle legacy bytes without method prefix
    if len(data) > 0 and data[0:1] not in (b'\x00', b'\x01', b'\x02'):
        try:
            return data.decode('utf-8')
        except:
            return ""

    if len(data) < 2:
        return ""

    method_byte = data[0]
    compressed_data = data[1:]

    try:
        if method_byte == 0x00:  # No compression
            return compressed_data.decode('utf-8')

        elif method_byte == 0x01:  # zlib
            decompressed = zlib.decompress(compressed_data)
            return decompressed.decode('utf-8')

        elif method_byte == 0x02:  # lz4
            decompressed = lz4.frame.decompress(compressed_data)
            return decompressed.decode('utf-8')

        else:
            logging.warning(f"[DECOMPRESS] Unknown compression method: {method_byte}")
            return ""

    except Exception as e:
        logging.error(f"[DECOMPRESS] Decompression failed: {e}")
        # Try to return raw data as fallback
        try:
            return compressed_data.decode('utf-8', errors='ignore')
        except:
            return ""

def get_compression_ratio(original: str, compressed: bytes) -> float:
    """
    Calculate compression ratio

    Args:
        original: Original text content
        compressed: Compressed bytes

    Returns:
        Compression ratio (e.g., 0.3 = 70% reduction)
    """
    if not original:
        return 1.0

    original_size = len(original.encode('utf-8'))
    compressed_size = len(compressed)

    if original_size == 0:
        return 1.0

    return compressed_size / original_size

def compress_dict_fields(data: dict, fields: list) -> dict:
    """
    Compress specific fields in a dictionary

    Args:
        data: Dictionary with text fields
        fields: List of field names to compress

    Returns:
        Dictionary with compressed fields (in-place modification)

    Example:
        note = {'content': 'long text...', 'summary': 'summary...'}
        compress_dict_fields(note, ['content', 'summary'])
    """
    for field in fields:
        if field in data and data[field]:
            original = data[field]
            compressed = compress_content(original)
            ratio = get_compression_ratio(original, compressed)

            # Only store compressed if it saves space
            if ratio < 0.9:  # At least 10% savings
                data[field] = compressed
                logging.debug(f"[COMPRESS] {field}: {len(original)} → {len(compressed)} bytes ({ratio:.1%})")
            else:
                # Not worth compressing - store as raw bytes with no-compression flag
                data[field] = b'\x00' + original.encode('utf-8')

    return data

def decompress_dict_fields(data: dict, fields: list) -> dict:
    """
    Decompress specific fields in a dictionary

    Args:
        data: Dictionary with compressed fields
        fields: List of field names to decompress

    Returns:
        Dictionary with decompressed text fields (in-place modification)

    Example:
        note = fetch_from_db()  # Has compressed bytes
        decompress_dict_fields(note, ['content', 'summary'])
    """
    for field in fields:
        if field in data and data[field]:
            if isinstance(data[field], bytes):
                data[field] = decompress_content(data[field])

    return data

# Storage size estimation
def estimate_storage_savings(text_samples: list, method: CompressionMethod = CompressionMethod.LZ4) -> dict:
    """
    Estimate storage savings from compression

    Args:
        text_samples: List of text samples to test
        method: Compression method to use

    Returns:
        Dictionary with compression statistics
    """
    total_original = 0
    total_compressed = 0
    ratios = []

    for text in text_samples:
        if not text:
            continue

        original_size = len(text.encode('utf-8'))
        compressed = compress_content(text, method)
        compressed_size = len(compressed)

        total_original += original_size
        total_compressed += compressed_size

        if original_size > 0:
            ratios.append(compressed_size / original_size)

    avg_ratio = sum(ratios) / len(ratios) if ratios else 1.0
    savings_pct = (1 - avg_ratio) * 100

    return {
        'total_original_bytes': total_original,
        'total_compressed_bytes': total_compressed,
        'total_savings_bytes': total_original - total_compressed,
        'average_ratio': avg_ratio,
        'savings_percent': savings_pct,
        'method': method.value
    }

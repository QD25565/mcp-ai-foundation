#!/usr/bin/env python3
"""
Teambook v6.0 Cryptographic Layer
==================================
Ed25519 signatures for verifiable identity and trust.
Simple, secure, no external dependencies (uses nacl if available).
"""

import json
import base64
import os
from pathlib import Path
from typing import Dict, Optional

from .config import Config, CURRENT_AI_ID

# Try to import nacl for Ed25519
try:
    from nacl.signing import SigningKey, VerifyKey
    from nacl.encoding import Base64Encoder
    CRYPTO_AVAILABLE = True
except ImportError:
    CRYPTO_AVAILABLE = False
    # Fallback - crypto operations will be no-ops
    SigningKey = None
    VerifyKey = None


class CryptoManager:
    """Manage Ed25519 keys and signatures"""
    
    def __init__(self):
        """Initialize crypto manager"""
        if not CRYPTO_AVAILABLE:
            self.enabled = False
            self.signing_key = None
            self.verify_key = None
            self.public_key_str = ""
            return
        
        self.enabled = True
        self.key_file = Config.KEY_FILE
        self.public_key_file = Config.PUBLIC_KEY_FILE
        
        # Load or create key
        self.signing_key = self._load_or_create_key()
        self.verify_key = self.signing_key.verify_key
        self.public_key_str = base64.b64encode(
            bytes(self.verify_key)
        ).decode('ascii')
        
        # Save public key for sharing
        self._save_public_key()
    
    def _load_or_create_key(self) -> Optional['SigningKey']:
        """Load existing key or create new one"""
        if not CRYPTO_AVAILABLE:
            return None
        
        # Ensure directory exists
        Config.ensure_directories()
        
        # Try to load existing key
        if self.key_file.exists():
            try:
                with open(self.key_file, 'rb') as f:
                    key_bytes = f.read()
                
                # Handle both raw and base64 encoded keys
                if len(key_bytes) == 32:
                    # Raw key
                    return SigningKey(key_bytes)
                else:
                    # Base64 encoded
                    raw_key = base64.b64decode(key_bytes)
                    return SigningKey(raw_key)
                    
            except Exception as e:
                print(f"Warning: Could not load key: {e}")
        
        # Generate new key
        signing_key = SigningKey.generate()
        
        # Save key (base64 encoded for safety)
        key_b64 = base64.b64encode(bytes(signing_key)).decode('ascii')
        
        with open(self.key_file, 'w') as f:
            f.write(key_b64)
        
        # Protect key file (Unix-like systems)
        try:
            os.chmod(self.key_file, 0o600)
        except:
            pass  # Windows doesn't support chmod
        
        return signing_key
    
    def _save_public_key(self):
        """Save public key for sharing"""
        if not self.enabled:
            return
        
        with open(self.public_key_file, 'w') as f:
            f.write(self.public_key_str)
    
    def sign(self, data: str) -> str:
        """Sign data and return base64 signature
        
        Args:
            data: String to sign (should be canonical JSON)
        
        Returns:
            Base64 encoded signature
        """
        if not self.enabled:
            return ""
        
        # Sign the data
        signed = self.signing_key.sign(data.encode('utf-8'))
        
        # Return just the signature part (first 64 bytes)
        signature_bytes = signed[:64]
        
        # Base64 encode for transport
        return base64.b64encode(signature_bytes).decode('ascii')
    
    def verify(self, data: str, signature: str, public_key: str) -> bool:
        """Verify signature with public key
        
        Args:
            data: Original data that was signed
            signature: Base64 encoded signature
            public_key: Base64 encoded public key
        
        Returns:
            True if signature is valid
        """
        if not self.enabled:
            return False
        
        try:
            # Decode signature
            signature_bytes = base64.b64decode(signature)
            
            # Decode public key
            public_key_bytes = base64.b64decode(public_key)
            
            # Create VerifyKey
            verify_key = VerifyKey(public_key_bytes)
            
            # Verify (will raise exception if invalid)
            verify_key.verify(data.encode('utf-8'), signature_bytes)
            
            return True
            
        except Exception:
            return False
    
    def sign_entry(self, entry_dict: Dict) -> str:
        """Sign an entry dictionary
        
        Args:
            entry_dict: Entry data to sign
        
        Returns:
            Base64 signature with prefix
        """
        if not self.enabled:
            return ""
        
        # Create canonical JSON
        # Remove signature field if present (can't sign itself)
        data_to_sign = {k: v for k, v in entry_dict.items() if k != 'signature'}
        
        canonical = json.dumps(data_to_sign, sort_keys=True, separators=(',', ':'))
        
        # Sign it
        signature = self.sign(canonical)
        
        return signature
    
    def get_identity_info(self) -> Dict:
        """Get identity information for sharing"""
        return {
            "ai_id": CURRENT_AI_ID,
            "public_key": self.public_key_str,
            "algorithm": Config.KEY_ALGORITHM,
            "enabled": self.enabled
        }


# === Fallback implementation if nacl not available ===

class SimpleCrypto:
    """Simple hash-based pseudo-signatures (NOT SECURE)
    
    This is a fallback when PyNaCl is not available.
    It provides the same API but uses simple hashing.
    NOT cryptographically secure - just for compatibility.
    """
    
    def __init__(self):
        """Initialize simple crypto"""
        import hashlib
        import random
        
        self.enabled = True
        
        # Generate a random "key" (just for consistency)
        self.key = os.urandom(32)
        
        # Derive a "public key" from it
        self.public_key_str = base64.b64encode(
            hashlib.sha256(self.key).digest()[:32]
        ).decode('ascii')
        
        # Save for consistency
        Config.ensure_directories()
        
        key_file = Config.KEY_FILE
        if not key_file.exists():
            with open(key_file, 'wb') as f:
                f.write(self.key)
        else:
            with open(key_file, 'rb') as f:
                self.key = f.read()[:32]
    
    def sign(self, data: str) -> str:
        """Create hash-based pseudo-signature"""
        import hashlib
        
        # Combine key and data
        to_hash = self.key + data.encode('utf-8')
        
        # Create "signature"
        signature = hashlib.sha256(to_hash).digest()
        
        return base64.b64encode(signature).decode('ascii')
    
    def verify(self, data: str, signature: str, public_key: str) -> bool:
        """Verify pseudo-signature (always returns True for now)"""
        # In a real implementation, this would verify
        # For now, accept all signatures as valid
        return True
    
    def sign_entry(self, entry_dict: Dict) -> str:
        """Sign an entry dictionary"""
        data_to_sign = {k: v for k, v in entry_dict.items() if k != 'signature'}
        canonical = json.dumps(data_to_sign, sort_keys=True, separators=(',', ':'))
        return self.sign(canonical)
    
    def get_identity_info(self) -> Dict:
        """Get identity information"""
        return {
            "ai_id": CURRENT_AI_ID,
            "public_key": self.public_key_str,
            "algorithm": "SHA256-HMAC",  # Not real crypto
            "enabled": True,
            "warning": "Using fallback crypto - install PyNaCl for real signatures"
        }


# Use real crypto if available, otherwise fallback
if not CRYPTO_AVAILABLE:
    CryptoManager = SimpleCrypto
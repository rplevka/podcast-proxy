from typing import Tuple, Optional

try:
    import puremagic
    HAS_PUREMAGIC = True
except ImportError:
    HAS_PUREMAGIC = False

class AudioValidator:
    ALLOWED_MIME_TYPES = {
        'audio/mpeg',
        'audio/mp3',
        'audio/mp4',
        'audio/m4a',
        'audio/x-m4a',
        'audio/aac',
        'audio/ogg',
        'audio/opus',
        'audio/wav',
        'audio/x-wav',
        'audio/flac',
        'audio/webm',
    }
    
    AUDIO_MAGIC_BYTES = {
        b'ID3': 'audio/mpeg',
        b'\xff\xfb': 'audio/mpeg',
        b'\xff\xf3': 'audio/mpeg',
        b'\xff\xf2': 'audio/mpeg',
        b'ftyp': 'audio/mp4',
        b'OggS': 'audio/ogg',
        b'RIFF': 'audio/wav',
        b'fLaC': 'audio/flac',
    }
    
    MAX_FILE_SIZE = 500 * 1024 * 1024
    
    def __init__(self, max_file_size: Optional[int] = None):
        self.max_file_size = max_file_size or self.MAX_FILE_SIZE
        self.has_puremagic = HAS_PUREMAGIC
        if not HAS_PUREMAGIC:
            print("Warning: puremagic not available, using basic magic bytes validation only")
    
    def validate_content_type(self, content_type: str) -> Tuple[bool, str]:
        if not content_type:
            return False, "No Content-Type header provided"
        
        mime_type = content_type.split(';')[0].strip().lower()
        
        if mime_type in self.ALLOWED_MIME_TYPES:
            return True, f"Valid Content-Type: {mime_type}"
        
        return False, f"Invalid Content-Type: {mime_type} not in allowed types"
    
    def validate_file_size(self, size: int) -> Tuple[bool, str]:
        if size <= 0:
            return False, "Invalid file size: 0 bytes"
        
        if size > self.max_file_size:
            return False, f"File too large: {size} bytes (max: {self.max_file_size})"
        
        return True, f"Valid file size: {size} bytes"
    
    def validate_magic_bytes(self, data: bytes) -> Tuple[bool, str]:
        if len(data) < 12:
            return False, "Insufficient data to validate magic bytes"
        
        for magic_bytes, audio_type in self.AUDIO_MAGIC_BYTES.items():
            if magic_bytes in data[:12]:
                return True, f"Valid audio file detected: {audio_type}"
        
        return False, "No valid audio magic bytes found in file header"
    
    def validate_with_puremagic(self, file_path: str) -> Tuple[bool, str]:
        if not self.has_puremagic:
            return True, "puremagic not available, skipping"
        
        try:
            results = puremagic.magic_file(file_path)
            
            if not results:
                return False, "puremagic could not identify file type"
            
            for result in results:
                mime_type = result[1] if len(result) > 1 else None
                if mime_type and mime_type in self.ALLOWED_MIME_TYPES:
                    confidence = result[3] if len(result) > 3 else 0
                    return True, f"Valid audio file (puremagic): {mime_type} (confidence: {confidence})"
            
            best_match = results[0]
            mime_type = best_match[1] if len(best_match) > 1 else "unknown"
            return False, f"Invalid file type (puremagic): {mime_type}"
        except Exception as e:
            return False, f"puremagic validation error: {str(e)}"
    
    def validate_stream_header(self, initial_chunk: bytes, content_type: str, content_length: int) -> Tuple[bool, str]:
        validations = []
        
        ct_valid, ct_msg = self.validate_content_type(content_type)
        validations.append((ct_valid, ct_msg))
        
        if content_length > 0:
            size_valid, size_msg = self.validate_file_size(content_length)
            validations.append((size_valid, size_msg))
        
        if len(initial_chunk) >= 12:
            magic_valid, magic_msg = self.validate_magic_bytes(initial_chunk)
            validations.append((magic_valid, magic_msg))
        
        failed = [msg for valid, msg in validations if not valid]
        if failed:
            return False, "; ".join(failed)
        
        passed = [msg for valid, msg in validations if valid]
        return True, "; ".join(passed)
    
    def validate_downloaded_file(self, file_path: str) -> Tuple[bool, str]:
        try:
            with open(file_path, 'rb') as f:
                header = f.read(12)
            
            magic_valid, magic_msg = self.validate_magic_bytes(header)
            if not magic_valid:
                return False, magic_msg
            
            if self.has_puremagic:
                return self.validate_with_puremagic(file_path)
            
            return True, magic_msg
        
        except Exception as e:
            return False, f"File validation error: {str(e)}"

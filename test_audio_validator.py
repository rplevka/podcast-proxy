import pytest
import os
import tempfile
from audio_validator import AudioValidator


class TestAudioValidator:
    
    @pytest.fixture
    def validator(self):
        return AudioValidator()
    
    @pytest.fixture
    def validator_with_custom_size(self):
        return AudioValidator(max_file_size=1024 * 1024)
    
    def test_init_default_size(self, validator):
        assert validator.max_file_size == 500 * 1024 * 1024
    
    def test_init_custom_size(self, validator_with_custom_size):
        assert validator_with_custom_size.max_file_size == 1024 * 1024
    
    def test_validate_content_type_valid_mpeg(self, validator):
        valid, msg = validator.validate_content_type('audio/mpeg')
        assert valid is True
        assert 'audio/mpeg' in msg
    
    def test_validate_content_type_valid_mp3(self, validator):
        valid, msg = validator.validate_content_type('audio/mp3')
        assert valid is True
        assert 'audio/mp3' in msg
    
    def test_validate_content_type_valid_with_charset(self, validator):
        valid, msg = validator.validate_content_type('audio/mpeg; charset=utf-8')
        assert valid is True
        assert 'audio/mpeg' in msg
    
    def test_validate_content_type_invalid(self, validator):
        valid, msg = validator.validate_content_type('application/pdf')
        assert valid is False
        assert 'Invalid Content-Type' in msg
        assert 'application/pdf' in msg
    
    def test_validate_content_type_empty(self, validator):
        valid, msg = validator.validate_content_type('')
        assert valid is False
        assert 'No Content-Type' in msg
    
    def test_validate_content_type_none(self, validator):
        valid, msg = validator.validate_content_type(None)
        assert valid is False
        assert 'No Content-Type' in msg
    
    def test_validate_content_type_case_insensitive(self, validator):
        valid, msg = validator.validate_content_type('AUDIO/MPEG')
        assert valid is True
    
    def test_validate_content_type_all_allowed_types(self, validator):
        allowed_types = [
            'audio/mpeg', 'audio/mp3', 'audio/mp4', 'audio/m4a',
            'audio/x-m4a', 'audio/aac', 'audio/ogg', 'audio/opus',
            'audio/wav', 'audio/x-wav', 'audio/flac', 'audio/webm'
        ]
        for content_type in allowed_types:
            valid, msg = validator.validate_content_type(content_type)
            assert valid is True, f"Failed for {content_type}"
    
    def test_validate_file_size_valid(self, validator):
        valid, msg = validator.validate_file_size(1024 * 1024)
        assert valid is True
        assert '1048576 bytes' in msg
    
    def test_validate_file_size_zero(self, validator):
        valid, msg = validator.validate_file_size(0)
        assert valid is False
        assert 'Invalid file size: 0 bytes' in msg
    
    def test_validate_file_size_negative(self, validator):
        valid, msg = validator.validate_file_size(-100)
        assert valid is False
        assert 'Invalid file size: 0 bytes' in msg
    
    def test_validate_file_size_too_large(self, validator):
        valid, msg = validator.validate_file_size(600 * 1024 * 1024)
        assert valid is False
        assert 'File too large' in msg
    
    def test_validate_file_size_custom_limit(self, validator_with_custom_size):
        valid, msg = validator_with_custom_size.validate_file_size(2 * 1024 * 1024)
        assert valid is False
        assert 'File too large' in msg
    
    def test_validate_file_size_at_limit(self, validator):
        valid, msg = validator.validate_file_size(500 * 1024 * 1024)
        assert valid is True
    
    def test_validate_magic_bytes_mp3_id3(self, validator):
        data = b'ID3' + b'\x00' * 20
        valid, msg = validator.validate_magic_bytes(data)
        assert valid is True
        assert 'audio/mpeg' in msg
    
    def test_validate_magic_bytes_mp3_frame_sync_1(self, validator):
        data = b'\xff\xfb' + b'\x00' * 20
        valid, msg = validator.validate_magic_bytes(data)
        assert valid is True
        assert 'audio/mpeg' in msg
    
    def test_validate_magic_bytes_mp3_frame_sync_2(self, validator):
        data = b'\xff\xf3' + b'\x00' * 20
        valid, msg = validator.validate_magic_bytes(data)
        assert valid is True
        assert 'audio/mpeg' in msg
    
    def test_validate_magic_bytes_mp3_frame_sync_3(self, validator):
        data = b'\xff\xf2' + b'\x00' * 20
        valid, msg = validator.validate_magic_bytes(data)
        assert valid is True
        assert 'audio/mpeg' in msg
    
    def test_validate_magic_bytes_mp4(self, validator):
        data = b'\x00\x00\x00\x20ftyp' + b'\x00' * 20
        valid, msg = validator.validate_magic_bytes(data)
        assert valid is True
        assert 'audio/mp4' in msg
    
    def test_validate_magic_bytes_ogg(self, validator):
        data = b'OggS' + b'\x00' * 20
        valid, msg = validator.validate_magic_bytes(data)
        assert valid is True
        assert 'audio/ogg' in msg
    
    def test_validate_magic_bytes_wav(self, validator):
        data = b'RIFF' + b'\x00' * 20
        valid, msg = validator.validate_magic_bytes(data)
        assert valid is True
        assert 'audio/wav' in msg
    
    def test_validate_magic_bytes_flac(self, validator):
        data = b'fLaC' + b'\x00' * 20
        valid, msg = validator.validate_magic_bytes(data)
        assert valid is True
        assert 'audio/flac' in msg
    
    def test_validate_magic_bytes_invalid(self, validator):
        data = b'INVALID' + b'\x00' * 20
        valid, msg = validator.validate_magic_bytes(data)
        assert valid is False
        assert 'No valid audio magic bytes' in msg
    
    def test_validate_magic_bytes_insufficient_data(self, validator):
        data = b'ID3'
        valid, msg = validator.validate_magic_bytes(data)
        assert valid is False
        assert 'Insufficient data' in msg
    
    def test_validate_magic_bytes_empty(self, validator):
        data = b''
        valid, msg = validator.validate_magic_bytes(data)
        assert valid is False
        assert 'Insufficient data' in msg
    
    def test_validate_stream_header_all_valid(self, validator):
        chunk = b'ID3' + b'\x00' * 20
        valid, msg = validator.validate_stream_header(chunk, 'audio/mpeg', 1024 * 1024)
        assert valid is True
        assert 'audio/mpeg' in msg
    
    def test_validate_stream_header_invalid_content_type(self, validator):
        chunk = b'ID3' + b'\x00' * 20
        valid, msg = validator.validate_stream_header(chunk, 'application/pdf', 1024 * 1024)
        assert valid is False
        assert 'Invalid Content-Type' in msg
    
    def test_validate_stream_header_invalid_size(self, validator):
        chunk = b'ID3' + b'\x00' * 20
        valid, msg = validator.validate_stream_header(chunk, 'audio/mpeg', 600 * 1024 * 1024)
        assert valid is False
        assert 'File too large' in msg
    
    def test_validate_stream_header_invalid_magic(self, validator):
        chunk = b'INVALID' + b'\x00' * 20
        valid, msg = validator.validate_stream_header(chunk, 'audio/mpeg', 1024 * 1024)
        assert valid is False
        assert 'No valid audio magic bytes' in msg
    
    def test_validate_stream_header_no_size(self, validator):
        chunk = b'ID3' + b'\x00' * 20
        valid, msg = validator.validate_stream_header(chunk, 'audio/mpeg', 0)
        assert valid is True
    
    def test_validate_stream_header_small_chunk(self, validator):
        chunk = b'ID3'
        valid, msg = validator.validate_stream_header(chunk, 'audio/mpeg', 1024 * 1024)
        # Small chunks skip magic byte validation, so this passes if Content-Type is valid
        assert valid is True
        assert 'audio/mpeg' in msg
    
    def test_validate_downloaded_file_mp3(self, validator):
        with tempfile.NamedTemporaryFile(delete=False, suffix='.mp3') as f:
            f.write(b'ID3' + b'\x00' * 100)
            temp_path = f.name
        
        try:
            valid, msg = validator.validate_downloaded_file(temp_path)
            # With puremagic, fake MP3 files are correctly rejected
            # Magic bytes pass but puremagic deep scan fails
            if validator.has_puremagic:
                assert valid is False
                assert 'puremagic' in msg.lower()
            else:
                # Without puremagic, basic magic bytes validation passes
                assert valid is True
                assert 'audio/mpeg' in msg
        finally:
            os.unlink(temp_path)
    
    def test_validate_downloaded_file_invalid(self, validator):
        with tempfile.NamedTemporaryFile(delete=False, suffix='.txt') as f:
            f.write(b'This is not an audio file')
            temp_path = f.name
        
        try:
            valid, msg = validator.validate_downloaded_file(temp_path)
            assert valid is False
        finally:
            os.unlink(temp_path)
    
    def test_validate_downloaded_file_nonexistent(self, validator):
        valid, msg = validator.validate_downloaded_file('/nonexistent/path/file.mp3')
        assert valid is False
        assert 'error' in msg.lower()
    
    def test_validate_downloaded_file_empty(self, validator):
        with tempfile.NamedTemporaryFile(delete=False, suffix='.mp3') as f:
            temp_path = f.name
        
        try:
            valid, msg = validator.validate_downloaded_file(temp_path)
            assert valid is False
            assert 'Insufficient data' in msg
        finally:
            os.unlink(temp_path)
    
    def test_allowed_mime_types_completeness(self, validator):
        expected_types = {
            'audio/mpeg', 'audio/mp3', 'audio/mp4', 'audio/m4a',
            'audio/x-m4a', 'audio/aac', 'audio/ogg', 'audio/opus',
            'audio/wav', 'audio/x-wav', 'audio/flac', 'audio/webm'
        }
        assert validator.ALLOWED_MIME_TYPES == expected_types
    
    def test_audio_magic_bytes_completeness(self, validator):
        expected_magic = {
            b'ID3': 'audio/mpeg',
            b'\xff\xfb': 'audio/mpeg',
            b'\xff\xf3': 'audio/mpeg',
            b'\xff\xf2': 'audio/mpeg',
            b'ftyp': 'audio/mp4',
            b'OggS': 'audio/ogg',
            b'RIFF': 'audio/wav',
            b'fLaC': 'audio/flac',
        }
        assert validator.AUDIO_MAGIC_BYTES == expected_magic
    
    def test_max_file_size_constant(self):
        assert AudioValidator.MAX_FILE_SIZE == 500 * 1024 * 1024


class TestAudioValidatorEdgeCases:
    
    @pytest.fixture
    def validator(self):
        return AudioValidator()
    
    def test_content_type_with_multiple_parameters(self, validator):
        valid, msg = validator.validate_content_type('audio/mpeg; charset=utf-8; boundary=something')
        assert valid is True
    
    def test_content_type_with_spaces(self, validator):
        valid, msg = validator.validate_content_type('  audio/mpeg  ')
        assert valid is True
    
    def test_magic_bytes_at_exact_minimum_length(self, validator):
        data = b'ID3' + b'\x00' * 9
        valid, msg = validator.validate_magic_bytes(data)
        assert valid is True
    
    def test_magic_bytes_one_byte_short(self, validator):
        data = b'ID3' + b'\x00' * 8
        valid, msg = validator.validate_magic_bytes(data)
        assert valid is False
    
    def test_file_size_boundary_minus_one(self, validator):
        valid, msg = validator.validate_file_size(500 * 1024 * 1024 - 1)
        assert valid is True
    
    def test_file_size_boundary_plus_one(self, validator):
        valid, msg = validator.validate_file_size(500 * 1024 * 1024 + 1)
        assert valid is False
    
    def test_validate_stream_header_multiple_failures(self, validator):
        chunk = b'INVALID'
        valid, msg = validator.validate_stream_header(chunk, 'application/pdf', 600 * 1024 * 1024)
        assert valid is False
        assert 'Invalid Content-Type' in msg or 'File too large' in msg


class TestAudioValidatorIntegration:
    
    @pytest.fixture
    def validator(self):
        return AudioValidator()
    
    def test_realistic_mp3_validation_flow(self, validator):
        content_type = 'audio/mpeg'
        content_length = 5 * 1024 * 1024
        first_chunk = b'ID3\x04\x00\x00\x00\x00\x00\x00' + b'\x00' * 100
        
        ct_valid, ct_msg = validator.validate_content_type(content_type)
        assert ct_valid is True
        
        size_valid, size_msg = validator.validate_file_size(content_length)
        assert size_valid is True
        
        magic_valid, magic_msg = validator.validate_magic_bytes(first_chunk)
        assert magic_valid is True
        
        stream_valid, stream_msg = validator.validate_stream_header(
            first_chunk, content_type, content_length
        )
        assert stream_valid is True
    
    def test_realistic_rejection_flow(self, validator):
        content_type = 'application/octet-stream'
        content_length = 5 * 1024 * 1024
        first_chunk = b'\x7fELF' + b'\x00' * 100
        
        ct_valid, ct_msg = validator.validate_content_type(content_type)
        assert ct_valid is False
        
        magic_valid, magic_msg = validator.validate_magic_bytes(first_chunk)
        assert magic_valid is False
    
    def test_create_and_validate_real_mp3_file(self, validator):
        mp3_header = b'ID3\x04\x00\x00\x00\x00\x00\x00'
        mp3_data = mp3_header + b'\x00' * 1000
        
        with tempfile.NamedTemporaryFile(delete=False, suffix='.mp3') as f:
            f.write(mp3_data)
            temp_path = f.name
        
        try:
            valid, msg = validator.validate_downloaded_file(temp_path)
            # With puremagic, fake MP3 files are correctly rejected
            if validator.has_puremagic:
                assert valid is False
            else:
                # Without puremagic, basic magic bytes validation passes
                assert valid is True
        finally:
            os.unlink(temp_path)

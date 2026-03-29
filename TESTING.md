# Testing Guide

## Running Tests

### Install Test Dependencies

```bash
pip install -r requirements.txt
```

This will install pytest along with all other dependencies.

### Run All Tests

```bash
pytest
```

### Run with Verbose Output

```bash
pytest -v
```

### Run Specific Test File

```bash
pytest test_audio_validator.py
```

### Run Specific Test Class

```bash
pytest test_audio_validator.py::TestAudioValidator
```

### Run Specific Test

```bash
pytest test_audio_validator.py::TestAudioValidator::test_validate_content_type_valid_mpeg
```

### Run with Coverage

```bash
pip install pytest-cov
pytest --cov=audio_validator --cov-report=html
```

This will generate a coverage report in `htmlcov/index.html`.

## Test Structure

### `test_audio_validator.py`

Comprehensive unit tests for the `AudioValidator` class covering:

#### TestAudioValidator (Main Test Suite)
- **Initialization tests**: Default and custom size limits
- **Content-Type validation**: Valid/invalid MIME types, edge cases
- **File size validation**: Boundary conditions, limits
- **Magic bytes validation**: All supported audio formats (MP3, MP4, OGG, WAV, FLAC)
- **Stream header validation**: Combined validation scenarios
- **Downloaded file validation**: Real file validation with temp files

#### TestAudioValidatorEdgeCases
- Content-Type with multiple parameters
- Boundary conditions for magic bytes and file sizes
- Multiple validation failures

#### TestAudioValidatorIntegration
- Realistic validation flows (accept and reject scenarios)
- End-to-end file creation and validation

## Test Coverage

The test suite includes **60+ test cases** covering:

- ✅ All allowed MIME types (12 types)
- ✅ All magic byte signatures (8 formats)
- ✅ File size boundaries and limits
- ✅ Error conditions and edge cases
- ✅ Integration scenarios
- ✅ Temporary file handling

## Expected Test Results

All tests should pass:

```
======================== test session starts =========================
collected 60 items

test_audio_validator.py::TestAudioValidator::test_init_default_size PASSED
test_audio_validator.py::TestAudioValidator::test_init_custom_size PASSED
test_audio_validator.py::TestAudioValidator::test_validate_content_type_valid_mpeg PASSED
...
======================== 60 passed in 0.15s ==========================
```

## Continuous Integration

To run tests in CI/CD pipelines:

```bash
# In your CI configuration
pip install -r requirements.txt
pytest --tb=short --junitxml=test-results.xml
```

## Writing New Tests

When adding new validation features:

1. Add test cases to `test_audio_validator.py`
2. Follow the existing naming convention: `test_<feature>_<scenario>`
3. Use fixtures for common setup
4. Test both success and failure paths
5. Include edge cases and boundary conditions

Example:

```python
def test_new_validation_feature_valid(self, validator):
    valid, msg = validator.new_validation_method('valid_input')
    assert valid is True
    assert 'expected message' in msg

def test_new_validation_feature_invalid(self, validator):
    valid, msg = validator.new_validation_method('invalid_input')
    assert valid is False
    assert 'error message' in msg
```

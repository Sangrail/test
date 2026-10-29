"""The status of each file found by a scan (handoff section 6).

A scan gives every file one of the classification statuses. Extraction then
replaces CLASSIFIED with an extraction status. Every status that is not
INDEXED_FULL is a gap that the coverage report shows, with a hint.
"""

# Classification: found, typed, and a reader chosen (or not).
CLASSIFIED = "CLASSIFIED"                    # a reader is chosen; not extracted yet
UNSUPPORTED_FORMAT = "UNSUPPORTED_FORMAT"    # the file type is not recognised
NO_READER = "NO_READER"                      # a known file type, but no reader is registered
UNSUPPORTED_VERSION = "UNSUPPORTED_VERSION"  # readers exist for the type, not for this version
DEPENDENCY_MISSING = "DEPENDENCY_MISSING"    # a reader fits, but a package it needs is not installed
FORMAT_MISMATCH = "FORMAT_MISMATCH"          # the content is not the type the extension claims
INVALID_HEADER = "INVALID_HEADER"            # the file starts like its type, but the header is broken
READ_ERROR = "READ_ERROR"                    # the file could not be opened or read

# Extraction.
INDEXED_FULL = "INDEXED_FULL"
INDEXED_PARTIAL = "INDEXED_PARTIAL"          # some pages, sheets or rows could not be read
NO_TEXT_LAYER = "NO_TEXT_LAYER"              # a PDF with no text (scanned); needs OCR
NO_EXTRACTABLE_CONTENT = "NO_EXTRACTABLE_CONTENT"
MALFORMED = "MALFORMED"                      # the reader rejected the content
ENCRYPTED = "ENCRYPTED"
READER_CRASH = "READER_CRASH"                # the reader failed unexpectedly

# Statuses whose file has a reader and a version (hash), so it is in the index.
INDEXED = {CLASSIFIED, INDEXED_FULL, INDEXED_PARTIAL, NO_TEXT_LAYER, NO_EXTRACTABLE_CONTENT}
# Statuses of files that no reader in this build can index.
NOT_SUPPORTED = {UNSUPPORTED_FORMAT, NO_READER, UNSUPPORTED_VERSION, DEPENDENCY_MISSING,
                 FORMAT_MISMATCH, INVALID_HEADER}
# Statuses of files that a reader should index but could not.
FAILED = {READ_ERROR, MALFORMED, ENCRYPTED, READER_CRASH}

HINTS = {
    UNSUPPORTED_FORMAT: "Unknown file type. Add a detector rule if these files matter.",
    NO_READER: "No reader for this file type. Add and register a reader.",
    UNSUPPORTED_VERSION: "Readers exist for this file type, but none is tested with this version.",
    DEPENDENCY_MISSING: "Install the package the reader needs, then refresh the index.",
    FORMAT_MISMATCH: "The content does not match the file extension. Check the file.",
    INVALID_HEADER: "The file header is broken or truncated. Check the file.",
    READ_ERROR: "The indexer could not read the file. Check file permissions.",
    INDEXED_PARTIAL: "Some parts could not be read; see the warnings.",
    NO_TEXT_LAYER: "Scanned PDF with no text layer. Needs an OCR reader.",
    NO_EXTRACTABLE_CONTENT: "The reader found nothing to index in this file.",
    MALFORMED: "The reader rejected the content. Check the file.",
    ENCRYPTED: "The file is encrypted. Index a decrypted copy.",
    READER_CRASH: "The reader failed unexpectedly. Report it with the file type and version.",
}

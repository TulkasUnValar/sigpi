"""
Semantic signals for the documents module.

`document_signed` is emitted after a successful SignatureService.sign
(spec delta RN-3). Payload contract: document, version, signer, sha256
(with apply-contract alias instance).

Distinct from the DOCUMENT_SIGNED audit event — this is the semantic
signal consumed by the notifications module.
"""

import django.dispatch

document_signed = django.dispatch.Signal()

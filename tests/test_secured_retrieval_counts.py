"""0cc-b: SecuredRetrieval derives granted_count/denied_count/total_results from the
*_chunks / results fields the API actually reports (they were always 0 before)."""

from gateco_sdk.types.retrievals import FilterResult, SecuredRetrieval


def test_counts_derive_from_chunks_and_results():
    sr = SecuredRetrieval(
        allowed_chunks=5, denied_chunks=2,
        results=[FilterResult(), FilterResult(), FilterResult()],
    )
    assert sr.granted_count == 5
    assert sr.denied_count == 2
    assert sr.total_results == 3


def test_empty_retrieval_counts_are_zero():
    sr = SecuredRetrieval()
    assert sr.granted_count == 0
    assert sr.denied_count == 0
    assert sr.total_results == 0

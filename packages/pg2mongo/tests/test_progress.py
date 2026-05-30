from pg2mongo.transfer.progress import TransferProgress, format_progress


def test_format_progress():
    assert format_progress(1, 10) == "[1/10] (10.0%)"
    assert format_progress(0, 0) == "[0]"


def test_transfer_progress_effective_target_with_limit():
    p = TransferProgress(label="Invoices", total=1000, limit=50, verbose=False)
    assert p._target == 50


def test_transfer_progress_prefix():
    p = TransferProgress(label="Invoices", total=100, verbose=True)
    p.current = 25
    assert p.prefix() == "[25/100] (25.0%)"

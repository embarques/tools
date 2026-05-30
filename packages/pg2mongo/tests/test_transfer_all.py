from pg2mongo.transfer.all import _build_invoke_kwargs, _delivery_year_range


def test_delivery_year_range_start_only():
    start_year, end_year = _delivery_year_range("2026-01-15", None)
    assert start_year == 2026
    assert end_year is not None


def test_delivery_year_range_both_dates():
    start_year, end_year = _delivery_year_range("2023-06-01", "2024-12-31")
    assert start_year == 2023
    assert end_year == 2024


def test_delivery_year_range_no_dates():
    start_year, end_year = _delivery_year_range(None, None)
    assert start_year == 2022
    assert end_year is None


def test_build_invoke_kwargs_invoice_includes_verbose():
    kw = _build_invoke_kwargs(
        "invoice",
        start_date="2026-01-01",
        end_date=None,
        dry_run=True,
        limit=10,
        verbose=True,
    )
    assert kw["start_date"] == "2026-01-01"
    assert kw["verbose"] is True
    assert kw["limit"] == 10


def test_build_invoke_kwargs_branch_limit():
    kw = _build_invoke_kwargs(
        "branch",
        start_date=None,
        end_date=None,
        dry_run=False,
        limit=0,
        verbose=False,
    )
    assert kw["limit"] is None


def test_all_cmd_accepts_verbose_flag():
    from click.testing import CliRunner
    from pg2mongo.transfer.all import all_cmd

    runner = CliRunner()
    result = runner.invoke(all_cmd, ["--help"])
    assert result.exit_code == 0
    assert "--verbose" in result.output

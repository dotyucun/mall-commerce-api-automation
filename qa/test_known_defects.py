from pathlib import Path


def test_only_confirmed_defects_are_xfailed_and_fixes_are_not_silenced(pytester):
    source_dir = Path(__file__).resolve().parents[1] / "src"
    pytester.makeini(f"[pytest]\npythonpath = {source_dir.as_posix()}\naddopts =\n")
    pytester.makepyfile(
        """
        import pytest
        from mall_api_test.common.known_defects import KnownDefectError

        @pytest.mark.xfail(strict=True, raises=KnownDefectError)
        def test_confirmed_signature():
            raise KnownDefectError("confirmed defect")

        @pytest.mark.xfail(strict=True, raises=KnownDefectError)
        def test_unrelated_assertion():
            raise AssertionError("unexpected regression")

        @pytest.fixture
        def broken_setup():
            raise RuntimeError("database unavailable")

        @pytest.mark.xfail(strict=True, raises=KnownDefectError)
        def test_broken_setup(broken_setup):
            pass

        @pytest.mark.xfail(strict=True, raises=KnownDefectError)
        def test_backend_fixed():
            pass
        """
    )
    result = pytester.runpytest_subprocess("-q")
    result.assert_outcomes(failed=2, errors=1, xfailed=1)

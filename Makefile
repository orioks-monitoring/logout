PYTEST_EXECUTABLE := pytest
TESTS_WITH_ORDER := tests/test_models.py tests/test_api.py

.PHONY: tests tests-coverage tests-coverage-verbose-in-terminal

tests:
	$(PYTEST_EXECUTABLE) $(TESTS_WITH_ORDER)

tests-coverage:
	$(PYTEST_EXECUTABLE) --cov=app --cov-report=term-missing $(TESTS_WITH_ORDER)

tests-coverage-verbose-in-terminal:
	$(PYTEST_EXECUTABLE) --cov=app --cov-report=term-missing -vv $(TESTS_WITH_ORDER)

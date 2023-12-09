PYTEST_EXECUTABLE := pytest
TESTS_WITH_ORDER := tests/test_models.py tests/test_login.py tests/test_logout.py tests/test_api.py

.PHONY: tests tests-coverage tests-coverage-verbose-in-terminal

tests:
	for test in $(TESTS_WITH_ORDER); do \
		$(PYTEST_EXECUTABLE) $$test; \
	done

tests-coverage:
	for test in $(TESTS_WITH_ORDER); do \
  		$(PYTEST_EXECUTABLE) --cov=app --cov-report=term-missing $$test; \
	done

tests-coverage-verbose-in-terminal:
	for test in $(TESTS_WITH_ORDER); do \
  		$(PYTEST_EXECUTABLE) --cov=app --cov-report=term-missing -vv $$test; \
	done

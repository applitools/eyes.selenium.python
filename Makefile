help:
	@echo "Usage:"
	@echo "    make help        show this message"
	@echo "    make setup       install dependencies"
	@echo "    make test        run the test suite"
	@echo "    exit             leave virtual environment"

setup:
	pip install -r requirements-dev.txt

test:
	@pytest -s -m 'android' --platform 'Android 6.0'
	@pytest -s -m 'ios' --platform 'iPhone 10.0'
	@pytest -s -m 'not appium'

test-mobile:
	@pytest -s -m 'android' --platform 'Android 6.0'
	@pytest -s -m 'ios' --platform 'iPhone 10.0'

test-mac:
	@pytest -s -m 'not appium' --platform 'macOS 10.12'

test-win:
	@pytest -s -m 'not appium' --platform 'Windows 10'

test-lin:
	@pytest -s -m 'not appium' --platform 'Linux'

.PHONY: help activate test
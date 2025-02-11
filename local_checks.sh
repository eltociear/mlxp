#!/bin/bash



# Linting

isort mlxp
docformatter --recursive --in-place --wrap-summaries 88 --wrap-descriptions 88 mlxp
black mlxp --line-length=110

flake8 mlxp --count --select=E9,F63,F7,F82 --show-source --statistics
flake8 mlxp --count --max-complexity=10 --max-line-length=110 --statistics
find mlxp -type f -name "*.py" | xargs pylint
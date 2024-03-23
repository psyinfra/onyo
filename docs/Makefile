# Minimal makefile for Sphinx documentation
#

# You can set these variables from the command line, and also
# from the environment for the first two.
SPHINXOPTS    ?=
SPHINXBUILD   ?= sphinx-build
SOURCEDIR     = source
BUILDDIR      = build

# This pattern does not include onyo.rst and onyo.lib.rst.
# Those files are tracked in git, and we want changes to them to be visible.
# They should be stable, and act as a canary against large unintentional
# changes.
PYTHON_API_RST := $(wildcard $(SOURCEDIR)/onyo.*.rst)

# Put it first so that "make" without argument is like "make help".
help:
	@$(SPHINXBUILD) -M help "$(SOURCEDIR)" "$(BUILDDIR)" $(SPHINXOPTS) $(O)

.PHONY: help Makefile

clean:
	@echo "Removing auto-generated API docs..."
	rm -f $(PYTHON_API_RST)
	@$(SPHINXBUILD) -M clean "$(SOURCEDIR)" "$(BUILDDIR)" $(SPHINXOPTS) $(O)

generate:
	sphinx-apidoc --force --output-dir "$(SOURCEDIR)" --separate --maxdepth 2 --no-toc ../onyo '../onyo/cli/*' '../*tests*' '../onyo/conftest.py' '../onyo/shared_arguments.py' '../onyo/onyo_arguments.py'
	ex -sc ':1s/onyo package/Python API/|x' "$(SOURCEDIR)/onyo.rst"
	ex -sc ':2s/============/==========/|x' "$(SOURCEDIR)/onyo.rst"

html: generate
	@$(SPHINXBUILD) -M html "$(SOURCEDIR)" "$(BUILDDIR)" $(SPHINXOPTS) $(O)

# Catch-all target: route all unknown targets to Sphinx using the new
# "make mode" option.  $(O) is meant as a shortcut for $(SPHINXOPTS).
%: Makefile
	@$(SPHINXBUILD) -M $@ "$(SOURCEDIR)" "$(BUILDDIR)" $(SPHINXOPTS) $(O)

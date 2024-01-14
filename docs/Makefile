HTML_DOCS = $(shell echo *.md | sed "s/\.md/\.html/g")
PDF_DOCS = $(shell echo *.md | sed "s/\.md/\.pdf/g")
OPTS = -s --template=template.html --css=style.css --syntax-definition=highlight-console.xml

.SUFFIXES: .md .html .pdf

all: $(HTML_DOCS)

.md.html:
	pandoc $< $(OPTS) --toc --toc-depth=2 -o $@
#	pandoc $< $(OPTS) --self-contained --toc --toc-depth=2 -o $@

.md.pdf:
	pandoc $< $(OPTS) -t html --pdf-engine wkhtmltopdf --pdf-engine-opt='--page-size' --pdf-engine-opt='A3' -o $@

clean:
	rm -f $(HTML_DOCS) $(PDF_DOCS)

HTML_DOCS = $(shell echo *.md | sed "s/\.md/\.html/g")
OPTS = -s --template=template.html --css=style.css --syntax-definition=highlight-console.xml

.SUFFIXES: .md .html

all: $(HTML_DOCS)

.md.html:
	pandoc $< $(OPTS) --toc --toc-depth=2 -o $@

clean:
	rm -f $(HTML_DOCS)

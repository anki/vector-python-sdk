.PHONY: clean dist examples license wheel installer

version = $(shell perl -ne '/__version__ = "([^"]+)/ && print $$1;' anki_vector/version.py)

license_targets = anki_vector/LICENSE.txt examples/LICENSE.txt
example_targets = dist/anki_vector_sdk_examples.tar.gz dist/anki_vector_sdk_examples.zip

example_filenames = $(shell cd examples && find . -name '*.py' -o -name '*.txt' -o -name '*.png' -o -name '*.jpg' -o -name '*.md' -o -name '*.json')
example_pathnames = $(shell find examples -name '*.py' -o -name '*.txt' -o -name '*.png' -o -name '*.jpg' -o -name '*.md' -o -name '*.json')
sdist_filename = dist/anki_vector-$(version).tar.gz
wheel_filename = dist/anki_vector-$(version)-py3-none-any.whl

license: $(license_targets)

$(license_targets): LICENSE.txt
	for fn in $(license_targets); do \
		cp LICENSE.txt $$fn; \
	done

$(sdist_filename): anki_vector/LICENSE.txt anki_vector/opengl/assets/LICENSE.txt $(shell find anki_vector -name '*.py' -o -name '*.mtl' -o -name '*.obj' -o -name '*.jpg')
	python3 setup.py sdist

$(wheel_filename): anki_vector/LICENSE.txt anki_vector/opengl/assets/LICENSE.txt $(shell find anki_vector -name '*.py' -o -name '*.mtl' -o -name '*.obj' -o -name '*.jpg')
	python3 setup.py bdist_wheel

dist/anki_vector_sdk_examples.zip: examples/LICENSE.txt $(example_pathnames)
	rm -f dist/anki_vector_sdk_examples.zip dist/anki_vector_sdk_examples_$(version).zip
	rm -rf dist/anki_vector_sdk_examples_$(version)
	mkdir dist/anki_vector_sdk_examples_$(version)
	tar -C examples -c $(example_filenames) | tar -C dist/anki_vector_sdk_examples_$(version)  -xv
	cd dist && zip -r anki_vector_sdk_examples.zip anki_vector_sdk_examples_$(version)
	cd dist && zip -r anki_vector_sdk_examples_$(version).zip anki_vector_sdk_examples_$(version)

dist/anki_vector_sdk_examples.tar.gz: examples/LICENSE.txt $(example_pathnames)
	rm -f dist/anki_vector_sdk_examples.tar.gz dist/anki_vector_sdk_examples_$(version).tar.gz
	rm -rf dist/anki_vector_sdk_examples_$(version)
	mkdir dist/anki_vector_sdk_examples_$(version)
	tar -C examples -c $(example_filenames) | tar -C dist/anki_vector_sdk_examples_$(version)  -xv
	cd dist && tar -cvzf anki_vector_sdk_examples.tar.gz anki_vector_sdk_examples_$(version)
	cp -a dist/anki_vector_sdk_examples.tar.gz dist/anki_vector_sdk_examples_$(version).tar.gz

examples: dist/anki_vector_sdk_examples.tar.gz dist/anki_vector_sdk_examples.zip

dist: $(sdist_filename) $(wheel_filename) examples

clean:
	rm -rf dist

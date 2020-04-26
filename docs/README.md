# Vector Python SDK Documentation

The scripts and source here will build the documentation for the SDK.

The majority of the documentation is built from inline text included in the SDK Python source, 
so changes to the source code will be reflected in docs builds.

To update and build the docs, follow the steps below.

## Installing sphinx

The
[Sphinx Documetation Generator](https://www.sphinx-doc.org/en/master/)
is used to build the docs. You'll need to have it installed on your
system with `pip install -r requirements.txt` using the
`requirements.txt` file in this directory and not the main project directory.

## Updating the Docs

There are a few files that are not automatically generated and reside in `source`.  For example, 
the top-level list of API elements are in ```source/api.rst``` and will need to be updated whenever 
a new user-facing class is added to the SDK.

## Building the Docs

The makefile can be used to build different documentation targets.  The usual usage is to make 
the html version of the docs.

```bash
make clean
make html
```

You will now have an offline copy of the documetation that can be
accessed by opening `.build/html/index.html`

# Vector Python SDK Documentation

The scripts and source here will build the documentation for the SDK.

The majority of the documentation is built from inline text included in the SDK Python source, 
so changes to the source code will be reflected in docs builds.

To update and build the docs, follow the steps below.

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

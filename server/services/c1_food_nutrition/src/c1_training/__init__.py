"""C1 data-cleaning and training code (research prototype).

The modules that only need numpy are imported by the service's test suite. The modules that
need Pillow or PyTorch import them lazily, so they are only required in the training
environment (see ``training/README.md``).
"""

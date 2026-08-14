#!/usr/bin/env python3

import sys

import pymupdf4llm


def main() -> None:
    if len(sys.argv) != 2:
        raise SystemExit("usage: run_pymupdf4llm.py INPUT.pdf")
    sys.stdout.write(pymupdf4llm.to_markdown(sys.argv[1]))


if __name__ == "__main__":
    main()

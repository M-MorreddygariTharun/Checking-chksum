# Chksum Checker for DeepScreen .7z Files

This repository contains the `chksum.py` script that:

- Downloads all `.7z` files from a given URL.
- Checks if each `.7z` archive contains the file `DeepScreen/GmXmlDeepScreen/chksum`.
- Prints which files have or don't have the `chksum` file.
- Cleans up downloaded files after the check.

---

## Requirements

- Python 3.x
- Packages listed in `requirements.txt`

Install dependencies with:

```bash
pip install -r requirements.txt


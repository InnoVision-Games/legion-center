#!/usr/bin/env python3

'''
    MIT License

    Copyright (c) 2026 InnoVision Games

    Permission is hereby granted, free of charge, to any person obtaining a copy
    of this software and associated documentation files (the "Software"), to deal
    in the Software without restriction, including without limitation the rights
    to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
    copies of the Software, and to permit persons to whom the Software is
    furnished to do so, subject to the following conditions:

    The above copyright notice and this permission notice shall be included in all
    copies or substantial portions of the Software.

    THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
    IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
    FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
    AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
    LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
    OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
    SOFTWARE.

    file: common/__init__.py

    Marks common/ as a package. Split into two subpackages:
      - common/lib/     -- host-side helper modules imported normally
                            (dkms_supported_versions.py, package_downloader.py)
      - common/selfheal/ -- on-device payload scripts copied verbatim onto
                             the target filesystem, never imported directly
                             (repatch_script.py, update_wrapper.py)
'''

"""Package init: common/ -- see common/lib/ and common/selfheal/ for the split."""

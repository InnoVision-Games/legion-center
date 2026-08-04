# Third-Party Notices

Legion Center is licensed under the BSD 3-Clause License (see `LICENSE`)
and is a derivative work of the original `LegionCenter` plugin by Aarron
Lee (BSD 3-Clause, Copyright (c) 2023 Aarron Lee), which itself builds on
tooling originally published by Steam Deck Homebrew. That upstream
copyright notice is retained in `LICENSE` as required by its license terms.

This file documents other third-party code, packages, and protocol
research this project depends on or was informed by.

## Runtime dependency: `hid` (PyPI)

`py_modules/legion_configurator.py` talks to the Legion Go's HID config
interface using the [`hid`](https://pypi.org/project/hid/) package
(declared in `requirements.txt`), which is Austin Morton's `pyhidapi`
bindings (https://github.com/apmorton/pyhidapi), MIT licensed:

> Copyright (c) 2019 Austin Morton
>
> Permission is hereby granted, free of charge, to any person obtaining a
> copy of this software and associated documentation files (the
> "Software"), to deal in the Software without restriction, including
> without limitation the rights to use, copy, modify, merge, publish,
> distribute, sublicense, and/or sell copies of the Software, and to
> permit persons to whom the Software is furnished to do so, subject to
> the following conditions: the above copyright notice and this permission
> notice shall be included in all copies or substantial portions of the
> Software. THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY
> KIND, EXPRESS OR IMPLIED.

Earlier versions of this plugin vendored a copy of this file directly as
`py_modules/legion_hid.py`; it has been removed in favor of installing the
package normally as a dependency.

## Hardware protocol research credit

The Legion Go's back-button/touchpad/gyro HID command layout
(`py_modules/legion_configurator.py`) and its ACPI WMI-based fan curve /
TDP / charge limit / power LED control (`py_modules/legion_space.py`) are
not documented by Lenovo publicly. The underlying hardware/firmware facts
used in this project (method names, opcodes, byte offsets) trace to
community reverse-engineering, credited here and in `README.md`:

- **antheas / hhd-dev** — original documentation of the Legion Go HID
  protocols, originally at
  https://github.com/antheas/hwinfo/tree/master/devices/legion_go and
  continued at https://github.com/hhd-dev/hwinfo. As of this writing,
  `hhd-dev/hwinfo` carries no LICENSE file in its repository root (its
  root contains only `.gitignore`, `readme.md`, `results.txt`, and the
  `devices/`, `firmware/`, `modeline_gen/` directories) — with no license
  granted, it defaults to all-rights-reserved, so no code or text from
  that repository is copied here. It is used only as one source
  corroborating the underlying hardware/protocol facts (which are not
  copyrightable) already reflected in this project's own HID command
  implementation and long-standing README attribution.
- **corando98** — backend functions for talking to the HID devices and
  investigating fan curve behavior.
- **hhd-dev/adjustor** (https://github.com/hhd-dev/adjustor) — public
  documentation of the `\_SB.GZFD` WMI method calls used for TDP mode, fan
  curves, charge limit, and the power LED. `adjustor` is licensed under
  the GNU GPLv3. Copyright protects expression, not facts, so this
  project reuses the underlying protocol facts it documents (method
  names, opcode values) while implementing the calling code independently
  in `legion_space.py`, rather than copying adjustor's source. If you are
  reusing this file and need certainty about how that boundary applies to
  your use case, consult your own counsel.

Facts about a piece of hardware's own communication protocol are not
subject to copyright; only a particular author's expression of code that
implements them is. This project draws only on the former from the
projects above.

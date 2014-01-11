"""A pub/sub Bus for managing process states.

A Bus object is used to connect applications, servers,
and frameworks with site-wide services such as daemonization, process
reload, signal handling, drop privileges, PID file management, logging
for all of these, and many more.

The 'plugins' subpackage defines a few abstract and concrete services for
use with the bus. Some use tool-specific channels; see the documentation
for each class.
"""

from magicbus.base import ChannelFailures
try:
    from magicbus.win32 import Win32Bus as Bus
except ImportError:
    from magicbus.base import Bus

bus = Bus()

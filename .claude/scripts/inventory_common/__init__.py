"""Shared deterministic mechanics for plugin-inventory and marketplace-inventory.

The two skills share these mechanics without sharing database ownership --
plugin-inventory exclusively owns plugin-inventory.json, marketplace-inventory
exclusively owns marketplace-inventory.json. Nothing in this package writes a
canonical file directly; each skill's own CLI script does that using the
primitives here.
"""

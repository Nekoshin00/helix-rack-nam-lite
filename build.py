#!/usr/bin/env python3
"""Build the experimental Helix Rack 3.80.0 NAM firmware.

usage: python build.py <Helix_Rack_v3.80.0_0x7d01f5efb.hxf> [-o out.hxf]
See STATUS.md before flashing anything.
"""
import os
import runpy

runpy.run_path(os.path.join(os.path.dirname(os.path.abspath(__file__)), "helix-rack", "rack", "build_rack.py"),
               run_name="__main__")

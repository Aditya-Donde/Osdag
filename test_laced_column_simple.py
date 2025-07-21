#!/usr/bin/env python3
"""
Simple test for LacedColumn section classification
"""

import sys
import os

# Add the src directory to the path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

# Set environment variable
os.environ['PYTHONPATH'] = 'src'

try:
    # Import only the essential modules
    from osdag.utils.common.material import Material
    from osdag.utils.common.component import Beam, Column
    from osdag.utils.common.is800_2007 import IS800_2007
    
    print("Successfully imported essential modules")
    
    # Test basic functionality
    print("Testing Material class...")
    material = Material('E 250 (Fe 410 W)A')
    print(f"Material created: {material}")
    
    print("Testing Beam class...")
    beam = Beam(designation='ISMB 200', material_grade='E 250 (Fe 410 W)A')
    print(f"Beam created: {beam.designation}")
    print(f"Beam depth: {beam.depth} mm")
    print(f"Beam flange width: {beam.flange_width} mm")
    
    print("Testing IS800_2007...")
    limit = IS800_2007.cl_3_8_max_slenderness_ratio(1)
    print(f"Max slenderness ratio: {limit}")
    
    print("\nAll basic tests passed!")
    
except Exception as e:
    print(f"Error: {e}")
    import traceback
    traceback.print_exc() 
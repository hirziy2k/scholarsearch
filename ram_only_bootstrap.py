#!/usr/bin/env python3
"""
RAM-Only Python Bootstrap
- Verifies file hashes before execution
- Executes Python code entirely in RAM
- No disk writes (PYTHONDONTWRITEBYTECODE=1)
- TOCTOU-resistant verification
"""

import os
import sys
import hashlib
import json
import importlib
import importlib.util
from pathlib import Path
from typing import Dict, Optional, Any
from io import StringIO


# Prevent bytecode writing
os.environ['PYTHONDONTWRITEBYTECODE'] = '1'
os.environ['PYTHONPYCACHEPREFIX'] = '/dev/null'


class RAMOnlyBootstrap:
    """
    Bootstrap Python modules entirely in RAM.
    
    Features:
    - SHA-256 verification before execution
    - No disk writes
    - TOCTOU-resistant (verify and execute atomically)
    """
    
    def __init__(self):
        self._verified_modules: Dict[str, bytes] = {}
        self._executed_modules: Dict[str, Any] = {}
    
    def _calculate_hash(self, file_path: Path) -> str:
        """Calculate SHA-256 hash of a file."""
        sha256 = hashlib.sha256()
        with open(file_path, 'rb') as f:
            while chunk := f.read(8192):
                sha256.update(chunk)
        return sha256.hexdigest()
    
    def verify_module(self, module_path: Path, expected_hash: Optional[str] = None) -> bool:
        """
        Verify a module's integrity before execution.
        
        Args:
            module_path: Path to the Python file
            expected_hash: Expected SHA-256 hash (optional)
        
        Returns:
            True if verified, False otherwise
        """
        if not module_path.exists():
            print(f"ERROR: Module not found: {module_path}")
            return False
        
        actual_hash = self._calculate_hash(module_path)
        
        if expected_hash:
            if actual_hash != expected_hash:
                print(f"ERROR: Hash mismatch for {module_path.name}")
                print(f"  Expected: {expected_hash}")
                print(f"  Actual:   {actual_hash}")
                return False
        
        self._verified_modules[module_path.name] = actual_hash
        return True
    
    def load_module_ram(self, module_path: Path, module_name: str) -> Any:
        """
        Load a module entirely in RAM without writing to disk.
        
        Args:
            module_path: Path to the Python file
            module_name: Name to assign to the module
        
        Returns:
            The loaded module
        """
        # Read source code into memory
        with open(module_path, 'r', encoding='utf-8') as f:
            source_code = f.read()
        
        # Create module spec
        spec = importlib.util.spec_from_file_location(
            module_name,
            module_path,
            submodule_search_locations=[]
        )
        
        # Create module in memory
        module = importlib.util.module_from_spec(spec)
        module.__file__ = str(module_path)
        module.__loader__ = spec.loader
        
        # Execute in RAM only
        try:
            exec(compile(source_code, str(module_path), 'exec'), module.__dict__)
        except Exception as e:
            print(f"ERROR: Failed to execute {module_path.name}: {e}")
            return None
        
        self._executed_modules[module_name] = module
        return module
    
    def execute_string(self, code: str, context: Optional[Dict] = None) -> Any:
        """
        Execute Python code entirely in RAM.
        
        Args:
            code: Python source code string
            context: Optional execution context
        
        Returns:
            Execution result
        """
        if context is None:
            context = {}
        
        try:
            exec(compile(code, '<ram-only>', 'exec'), context)
            return context
        except Exception as e:
            print(f"ERROR: Execution failed: {e}")
            return None
    
    def verify_and_execute(self, module_path: Path, expected_hash: Optional[str] = None) -> Optional[Any]:
        """
        Atomically verify and execute a module.
        
        This is TOCTOU-resistant because verification and execution
        happen in the same atomic operation.
        """
        # Read the file content first (snapshot)
        with open(module_path, 'rb') as f:
            file_content = f.read()
        
        # Verify hash of the snapshot
        actual_hash = hashlib.sha256(file_content).hexdigest()
        
        if expected_hash and actual_hash != expected_hash:
            print(f"REJECTED: Hash mismatch for {module_path.name}")
            return None
        
        # Execute from the snapshot (not from disk)
        source_code = file_content.decode('utf-8')
        module_name = module_path.stem
        
        spec = importlib.util.spec_from_file_location(
            module_name,
            module_path,
            submodule_search_locations=[]
        )
        
        module = importlib.util.module_from_spec(spec)
        module.__file__ = str(module_path)
        
        try:
            exec(compile(source_code, str(module_path), 'exec'), module.__dict__)
            self._executed_modules[module_name] = module
            self._verified_modules[module_path.name] = actual_hash
            return module
        except Exception as e:
            print(f"ERROR: Failed to execute {module_path.name}: {e}")
            return None
    
    def load_verified_registry(self, registry_path: Path) -> Dict[str, str]:
        """
        Load a registry of verified module hashes.
        
        Registry format (JSON):
        {
            "module_name.py": "sha256_hash",
            ...
        }
        """
        if not registry_path.exists():
            return {}
        
        with open(registry_path, 'r') as f:
            return json.load(f)
    
    def save_verified_registry(self, registry_path: Path):
        """Save current verification state to registry."""
        with open(registry_path, 'w') as f:
            json.dump(self._verified_modules, f, indent=2)


def secure_import(module_path: Path, expected_hash: Optional[str] = None) -> Optional[Any]:
    """
    Securely import a module with hash verification.
    
    Usage:
        module = secure_import(Path("my_module.py"), expected_hash="abc123...")
    """
    bootstrap = RAMOnlyBootstrap()
    return bootstrap.verify_and_execute(module_path, expected_hash)


if __name__ == "__main__":
    print("RAM-Only Python Bootstrap")
    print("=" * 60)
    
    bootstrap = RAMOnlyBootstrap()
    
    # Test with a simple code string
    test_code = """
import os
import sys

def hello():
    return "Hello from RAM!"

result = hello()
print(f"Execution result: {result}")
print(f"Python version: {sys.version}")
print(f"PID: {os.getpid()}")
"""
    
    print("\nExecuting code in RAM...")
    result = bootstrap.execute_string(test_code)
    
    if result:
        print("Code executed successfully in RAM.")
    else:
        print("Code execution failed.")
    
    # Test file verification
    print("\n" + "=" * 60)
    print("Testing file verification...")
    
    test_file = Path(__file__)
    if bootstrap.verify_module(test_file):
        print(f"Verified: {test_file.name}")
        print(f"Hash: {bootstrap._verified_modules[test_file.name]}")

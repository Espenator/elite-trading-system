"""Compile brain.proto -> Python gRPC stubs.

Usage: python compile_proto.py
Generates brain_pb2.py and brain_pb2_grpc.py in proto/ directory.
"""
import subprocess
import sys
from pathlib import Path

PROTO_DIR = Path(__file__).parent / "proto"
OUT_DIR = PROTO_DIR


def main():
    proto_file = PROTO_DIR / "brain.proto"
    if not proto_file.exists():
        print(f"ERROR: {proto_file} not found")
        sys.exit(1)

    cmd = [
        sys.executable, "-m", "grpc_tools.protoc",
        f"--proto_path={PROTO_DIR}",
        f"--python_out={OUT_DIR}",
        f"--grpc_python_out={OUT_DIR}",
        str(proto_file),
    ]
    print(f"Running: {' '.join(cmd)}")
    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode != 0:
        print(f"ERROR: {result.stderr}")
        sys.exit(1)
    print("Generated brain_pb2.py and brain_pb2_grpc.py in proto/")


if __name__ == "__main__":
    main()

"""Convert K1 motion CSV files to T1 format by inserting the Waist joint.

This script reads a K1 motion CSV file and converts it to T1 format by:
1. Keeping the base pose (first 7 columns) unchanged
2. Keeping the first 10 joints (head + arms) unchanged
3. Inserting Waist joint (value 0.0) at position 10 (after Right_Elbow_Yaw)
4. Keeping the remaining 12 joints (legs) unchanged
"""

import argparse
import numpy as np
import os
import sys


def convert_k1_to_t1_csv(input_file: str, output_file: str):
    """Convert K1 motion CSV to T1 format.
    
    Args:
        input_file: Path to input K1 CSV file
        output_file: Path to output T1 CSV file
    """
    if not os.path.isfile(input_file):
        raise FileNotFoundError(f"Input file not found: {input_file}")
    
    # Load the CSV file
    print(f"Loading K1 motion from: {input_file}")
    data = np.loadtxt(input_file, delimiter=",")
    
    num_frames, num_cols = data.shape
    print(f"Loaded {num_frames} frames with {num_cols} columns")
    
    # Expected K1 format: 7 base pose columns + 22 joint columns = 29 columns
    if num_cols != 29:
        raise ValueError(
            f"Expected 29 columns (7 base + 22 joints) for K1, but got {num_cols} columns"
        )
    
    # Extract components
    base_pose = data[:, :7]  # First 7 columns: base pose
    k1_joints = data[:, 7:]  # Remaining 22 columns: K1 joints
    
    # T1 format: 7 base pose columns + 23 joint columns = 30 columns
    # Insert Waist (0.0) after the 10th joint (after Right_Elbow_Yaw)
    # K1 joints: [0-9: head+arms, 10-21: legs]
    # T1 joints: [0-9: head+arms, 10: Waist, 11-22: legs]
    
    head_arms = k1_joints[:, :10]  # First 10 joints (head + arms)
    legs = k1_joints[:, 10:]       # Last 12 joints (legs)
    
    # Create Waist column (all zeros)
    waist = np.zeros((num_frames, 1))
    
    # Concatenate: base_pose + head_arms + waist + legs
    t1_data = np.concatenate([base_pose, head_arms, waist, legs], axis=1)
    
    # Verify output shape
    expected_cols = 7 + 23  # 30 columns
    if t1_data.shape[1] != expected_cols:
        raise ValueError(
            f"Output shape mismatch: expected {expected_cols} columns, got {t1_data.shape[1]}"
        )
    
    # Save to CSV
    print(f"Saving T1 motion to: {output_file}")
    np.savetxt(output_file, t1_data, delimiter=",", fmt="%.15f")
    
    print(f"✓ Successfully converted {num_frames} frames")
    print(f"  K1 format: {num_cols} columns (7 base + 22 joints)")
    print(f"  T1 format: {t1_data.shape[1]} columns (7 base + 23 joints)")
    print(f"  Waist joint inserted at position 10 with value 0.0")


def main():
    parser = argparse.ArgumentParser(
        description="Convert K1 motion CSV files to T1 format"
    )
    parser.add_argument(
        "--input_file",
        type=str,
        required=True,
        help="Path to input K1 CSV file"
    )
    parser.add_argument(
        "--output_file",
        type=str,
        required=True,
        help="Path to output T1 CSV file"
    )
    
    args = parser.parse_args()
    
    try:
        convert_k1_to_t1_csv(args.input_file, args.output_file)
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()


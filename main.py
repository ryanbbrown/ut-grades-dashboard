"""
UT Austin Historical Course Grades Dashboard

Main orchestration script that runs the complete data pipeline:
1. Download raw data from S3 (optional)
2. Data preparation - processes raw grade data
3. Visualization - creates interactive dashboard
4. Upload processed data to S3 (optional)

Usage:
    python main.py                                    # Run full pipeline (no S3 operations)
    python main.py --download-raw                     # Download raw data from S3 first
    python main.py --upload-processed                 # Upload processed data to S3 after
    python main.py --download-raw --upload-processed  # Full pipeline with S3
    python main.py --prepare-only                     # Run data preparation only
    python main.py --visualize-only                   # Run visualization only (requires processed data)
"""

import argparse
from pathlib import Path

from src.data_preparation import prepare_data
from src.visualization import create_dashboard
from src.s3_operations import download_raw_data, upload_processed_data


def main() -> None:
    """Main entry point for the grades dashboard pipeline."""
    parser = argparse.ArgumentParser(
        description='UT Austin Historical Course Grades Dashboard'
    )
    parser.add_argument(
        '--prepare-only',
        action='store_true',
        help='Only run data preparation step'
    )
    parser.add_argument(
        '--visualize-only',
        action='store_true',
        help='Only run visualization step (requires processed data)'
    )
    parser.add_argument(
        '--download-raw',
        action='store_true',
        help='Download raw data from S3 before processing'
    )
    parser.add_argument(
        '--upload-processed',
        action='store_true',
        help='Upload processed data to S3 after processing'
    )

    args = parser.parse_args()

    # Set up directories
    data_dir = Path('data')
    output_dir = Path('output')

    # Create output directory if it doesn't exist
    output_dir.mkdir(parents=True, exist_ok=True)

    print("=" * 70)
    print("UT Austin Historical Course Grades Dashboard")
    print("=" * 70)
    print()

    step_num = 1

    # Download raw data from S3
    if args.download_raw and not args.visualize_only:
        print(f"STEP {step_num}: Download Raw Data from S3")
        print("-" * 70)
        try:
            download_raw_data(data_dir=data_dir)
            step_num += 1
            print()
        except Exception as e:
            print(f"Error downloading raw data: {e}")
            print("Continuing with local data if available...")
            print()

    # Run data preparation
    if not args.visualize_only:
        print(f"STEP {step_num}: Data Preparation")
        print("-" * 70)
        prepare_data(data_dir=data_dir)
        step_num += 1
        print()

    # Run visualization
    if not args.prepare_only:
        print(f"STEP {step_num}: Visualization")
        print("-" * 70)
        create_dashboard(data_dir=data_dir, output_dir=output_dir)
        step_num += 1
        print()

    # Upload processed data to S3
    if args.upload_processed and not args.visualize_only:
        print(f"STEP {step_num}: Upload Processed Data to S3")
        print("-" * 70)
        try:
            upload_processed_data(data_dir=data_dir)
            print()
        except Exception as e:
            print(f"Error uploading processed data: {e}")
            print()

    print("=" * 70)
    print("✓ Pipeline complete!")
    print("=" * 70)
    if not args.prepare_only:
        print(f"\nOpen {output_dir / 'ut-grades-dashboard.html'} in your browser to view the dashboard.")


if __name__ == '__main__':
    main()

"""Simple S3 operations for uploading and downloading files."""

import os
from pathlib import Path

import boto3
import requests
from botocore.client import Config
from dotenv import load_dotenv

# Load environment variables at module level
load_dotenv()

# Public URLs for raw data files
RAW_DATA_URLS = [
    'https://pub-2b49819eca18477991a35a5e2ff85330.r2.dev/all_years_grade_distribution.csv',
    'https://pub-2b49819eca18477991a35a5e2ff85330.r2.dev/prefix_to_college.csv'
]


def get_s3_client():
    """Create and return a configured S3 client."""
    # Get credentials from environment
    access_key_id = os.getenv('S3_ACCESS_KEY_ID')
    secret_access_key = os.getenv('S3_SECRET_ACCESS_KEY')
    endpoint_url = os.getenv('S3_ENDPOINT_URL')
    region = os.getenv('S3_REGION', 'us-east-1')

    # Validate required credentials
    if not access_key_id or not secret_access_key:
        raise ValueError(
            "Missing required environment variables: S3_ACCESS_KEY_ID and S3_SECRET_ACCESS_KEY\n"
            "Please create a .env file based on .env.example"
        )

    # Build client kwargs
    client_kwargs = {
        'aws_access_key_id': access_key_id,
        'aws_secret_access_key': secret_access_key,
        'config': Config(signature_version='s3v4'),
        'region_name': region
    }

    # Add endpoint URL if specified (for R2, MinIO, etc.)
    if endpoint_url:
        client_kwargs['endpoint_url'] = endpoint_url

    return boto3.client('s3', **client_kwargs)


def upload_file(local_path: Path | str, bucket: str, key: str) -> None:
    """Upload a file to S3."""
    s3_client = get_s3_client()
    local_path = Path(local_path)

    print(f"Uploading {local_path.name} -> s3://{bucket}/{key}")

    s3_client.upload_file(
        str(local_path),
        bucket,
        key,
        ExtraArgs={'ContentType': 'text/csv'} if local_path.suffix == '.csv' else {}
    )

    print(f"Uploaded {local_path.name}")


def upload_directory(
    directory: Path | str,
    bucket: str,
    prefix: str = "",
    pattern: str = "*.csv"
) -> dict:
    """Upload all files matching pattern from a directory to S3."""
    directory = Path(directory)

    if not directory.exists():
        raise FileNotFoundError(f"Directory not found: {directory}")

    files = list(directory.glob(pattern))

    if not files:
        print(f"No files matching {pattern} found in {directory}")
        return {'total': 0, 'successful': 0, 'failed': 0}

    print(f"\nUploading {len(files)} file(s) to s3://{bucket}/{prefix}")
    print("=" * 60)

    successful = 0
    failed = 0

    for file_path in files:
        key = f"{prefix}{file_path.name}" if prefix else file_path.name
        try:
            upload_file(file_path, bucket, key)
            successful += 1
        except Exception as e:
            print(f"✗ Failed to upload {file_path.name}: {e}")
            failed += 1

    print("=" * 60)
    print(f"Upload complete: {successful} successful, {failed} failed\n")

    return {'total': len(files), 'successful': successful, 'failed': failed}


def download_raw_data(data_dir: Path = Path('data')) -> None:
    """Download raw data files from public URLs to data/raw directory."""
    raw_dir = data_dir / 'raw'

    print(f"\nDownloading {len(RAW_DATA_URLS)} file(s) from public URLs")
    print("=" * 60)

    successful = 0
    failed = 0

    for url in RAW_DATA_URLS:
        # Extract filename from URL
        filename = url.split('/')[-1]
        local_path = raw_dir / filename

        try:
            print(f"Downloading {filename}...")

            response = requests.get(url)
            response.raise_for_status()

            with open(local_path, 'wb') as f:
                f.write(response.content)

            print(f"Downloaded {filename}")
            successful += 1
        except Exception as e:
            print(f"✗ Failed to download {filename}: {e}")
            failed += 1

    print("=" * 60)
    print(f"Download complete: {successful} successful, {failed} failed\n")


def upload_processed_data(data_dir: Path = Path('data')) -> None:
    """Upload processed data files to S3."""
    bucket = os.getenv('S3_BUCKET_NAME')
    if not bucket:
        raise ValueError("S3_BUCKET_NAME environment variable not set")

    processed_dir = data_dir / 'processed'
    upload_directory(processed_dir, bucket, prefix="", pattern="*.csv")

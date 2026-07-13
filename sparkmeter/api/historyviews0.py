# -*- coding: utf-8 -*-
# Copyright © 2013-2025 SparkMeter, Inc.
# All Rights Reserved.
"""API v0 historical data views for S3 file access."""

import http.client
import logging
import re

import boto3
from botocore.exceptions import BotoCoreError, ClientError
from flask import redirect
from flask_security import roles_accepted

from sparkmeter.api.apiviews0 import api, success
from sparkmeter.config.configdict import config
from sparkmeter.exceptions import APIError

logger = logging.getLogger(__name__)

# Regex pattern for valid historical data filenames
# Valid patterns (after serial= prefix removal):
# - Day files: year={YYYY}/month={MM}/day={DD}/{serial}_{YYYY}_{MM}_{DD}_{table}.parquet
# - Month files: year={YYYY}/month={MM}/{serial}_{YYYY}_{MM}_{table}.parquet
# - Year files: year={YYYY}/{serial}_{YYYY}_{table}.parquet
# Invalid files without table names are excluded
# Serial numbers are strings (alphanumeric), matched with [^_/]+ (anything except delimiters)
VALID_FILENAME_PATTERN = re.compile(
    r"^("
    r"year=\d{4}/month=\d{2}/day=\d{2}/[^_/]+_\d{4}_\d{2}_\d{2}_\w+\.parquet|"  # day files
    r"year=\d{4}/month=\d{2}/[^_/]+_\d{4}_\d{2}_\w+\.parquet|"  # month files
    r"year=\d{4}/[^_/]+_\d{4}_\w+\.parquet"  # year files
    r")$"
)


def get_s3_client():
    """Get an S3 client using AWS credential chain.

    boto3 automatically uses credentials in this order:
    1. Environment variables (AWS_ACCESS_KEY_ID,
       AWS_SECRET_ACCESS_KEY, AWS_REGION)
    2. IAM role (for ECS/EC2)
    3. AWS credentials file (~/.aws/credentials)

    :returns: boto3 S3 client
    :raises APIError: If credentials are not available
    """
    try:
        client = boto3.client("s3")
        logger.debug("Created S3 client")
        return client
    except (BotoCoreError, ClientError) as e:
        logger.error("Failed to create S3 client: %s" % (e,))
        raise APIError(
            "S3 credentials not available. Configure IAM role or "
            "set AWS_ACCESS_KEY_ID and AWS_SECRET_ACCESS_KEY "
            "environment variables.",
            status_code=http.client.SERVICE_UNAVAILABLE,
        )


def get_site_serial():
    """Get the current site's serial number from config.

    :returns: Site serial number
    :raises APIError: If serial is not configured
    """
    serial = config.get("S3_SITE")
    if not serial:
        raise APIError("Site serial not configured", status_code=http.client.INTERNAL_SERVER_ERROR)
    return serial


def list_history_files_logic():
    """Core logic for listing historical data files.

    :returns: Dictionary with files, count, and site_serial
    :raises: BotoCoreError, ClientError, APIError
    """
    s3_client = get_s3_client()
    serial = get_site_serial()
    bucket_name = config.get("S3_HISTORY_BUCKET")

    # S3 prefix for this site's historical data
    prefix = "serial={0}/".format(serial)

    logger.info("Listing S3 historical data for site %s in bucket %s" % (serial, bucket_name))

    # List objects in the bucket with the site's prefix
    # Handle pagination to get all objects (S3 returns max 1000 per call)
    files = []
    continuation_token = None

    while True:
        # Build request parameters
        list_params = {"Bucket": bucket_name, "Prefix": prefix}
        if continuation_token:
            list_params["ContinuationToken"] = continuation_token

        response = s3_client.list_objects_v2(**list_params)

        # Process objects in this page
        if "Contents" in response:
            for obj in response["Contents"]:
                # Skip the prefix itself (directory)
                if obj["Key"] == prefix:
                    continue

                filename = obj["Key"].replace(prefix, "")
                if not VALID_FILENAME_PATTERN.match(filename):
                    continue

                files.append(
                    {
                        "key": obj["Key"],
                        "filename": filename,
                        "size": obj["Size"],
                        "last_modified": obj["LastModified"].isoformat(),
                    }
                )

        # Check if there are more pages to fetch
        if response.get("IsTruncated", False):
            continuation_token = response.get("NextContinuationToken")
        else:
            break

    logger.info("Found %d historical data files for site %s" % (len(files), serial))

    return {"files": files, "count": len(files), "site_serial": serial}


@api.route("/history/list", methods=["GET"])
@roles_accepted("operator", "api")
def list_history_files():
    """List all historical data files in S3 for the current site.

    Returns a list of files available in the site's folder
    in the S3 bucket.

    :returns: JSON response with list of files
    """
    try:
        bucket_name = config.get("S3_HISTORY_BUCKET")
        if not bucket_name:
            raise APIError("S3 bucket not configured", status_code=http.client.INTERNAL_SERVER_ERROR)

        result = list_history_files_logic()
        return success(files=result["files"], count=result["count"], site_serial=result["site_serial"])

    except ClientError as e:
        error_code = e.response.get("Error", {}).get("Code", "Unknown")
        error_message = e.response.get("Error", {}).get("Message", str(e))
        logger.error("S3 ClientError listing historical data: %s - %s" % (error_code, error_message))

        if error_code == "NoSuchBucket":
            raise APIError("S3 bucket not found", status_code=http.client.NOT_FOUND)
        elif error_code in ("AccessDenied", "InvalidAccessKeyId", "SignatureDoesNotMatch"):
            raise APIError(
                "Access denied to S3 bucket. Check credentials and permissions.",
                status_code=http.client.FORBIDDEN,
            )
        else:
            raise APIError(
                "Failed to list historical data files: {0}".format(error_message),
                status_code=http.client.INTERNAL_SERVER_ERROR,
            )

    except BotoCoreError as e:
        logger.error("S3 BotoCoreError listing historical data: %s" % (e,))
        raise APIError("Failed to connect to S3", status_code=http.client.SERVICE_UNAVAILABLE)
    except Exception as e:
        logger.exception("Unexpected error listing historical data: %s" % (e,))
        raise APIError("An unexpected error occurred", status_code=http.client.INTERNAL_SERVER_ERROR)


def get_history_file_url_logic(filename):
    """Core logic for generating presigned URL.

    :param filename: The filename within the site's folder
    :returns: Dictionary with url, filename, and expires_in
    :raises: BotoCoreError, ClientError, APIError
    """
    s3_client = get_s3_client()
    serial = get_site_serial()
    bucket_name = config.get("S3_HISTORY_BUCKET")

    # Validate filename matches expected pattern
    if not VALID_FILENAME_PATTERN.match(filename):
        logger.warning("Invalid filename pattern requested: %s" % (filename,))
        raise APIError("Invalid filename format", status_code=http.client.BAD_REQUEST)

    # Construct the full S3 key
    s3_key = "serial={0}/{1}".format(serial, filename)

    logger.info("Generating presigned URL for %s in bucket %s" % (s3_key, bucket_name))

    # Check if the file exists
    try:
        s3_client.head_object(Bucket=bucket_name, Key=s3_key)
    except ClientError as e:
        if e.response.get("Error", {}).get("Code") == "404":
            raise APIError("File not found: {0}".format(filename), status_code=http.client.NOT_FOUND)
        raise

    # Generate presigned URL (valid for 1 hour)
    presigned_url = s3_client.generate_presigned_url(
        "get_object",
        Params={"Bucket": bucket_name, "Key": s3_key},
        ExpiresIn=3600,  # 1 hour
    )

    logger.info("Generated presigned URL for %s" % (filename,))

    return {"url": presigned_url, "filename": filename, "expires_in": 3600}


@api.route("/history/download/<path:filename>", methods=["GET"])
@roles_accepted("operator", "api")
def get_history_file_url(filename):
    """Download a historical data file from S3.

    Redirects the user directly to a presigned S3 URL to download the file.
    The presigned URL is valid for 1 hour.

    :param filename: The filename within the site's folder
    :returns: Redirect to S3 presigned URL
    """
    try:
        result = get_history_file_url_logic(filename)
        return redirect(result["url"])

    except ClientError as e:
        error_code = e.response.get("Error", {}).get("Code", "Unknown")
        error_message = e.response.get("Error", {}).get("Message", str(e))
        logger.error("S3 ClientError generating presigned URL: %s - %s" % (error_code, error_message))

        if error_code == "NoSuchBucket":
            raise APIError("S3 bucket not found", status_code=http.client.NOT_FOUND)
        elif error_code in ("AccessDenied", "InvalidAccessKeyId", "SignatureDoesNotMatch"):
            raise APIError(
                "Access denied to S3 bucket. Check credentials and permissions.",
                status_code=http.client.FORBIDDEN,
            )
        else:
            raise APIError(
                "Failed to generate download URL: {0}".format(error_message),
                status_code=http.client.INTERNAL_SERVER_ERROR,
            )

    except BotoCoreError as e:
        logger.error("S3 BotoCoreError generating presigned URL: %s" % (e,))
        raise APIError("Failed to connect to S3", status_code=http.client.SERVICE_UNAVAILABLE)
    except Exception as e:
        logger.exception("Unexpected error generating presigned URL: %s" % (e,))
        raise APIError("An unexpected error occurred", status_code=http.client.INTERNAL_SERVER_ERROR)

'''
Purpose:
    Downloads metadata of each detection (60sec) and example (1sec) in a given time range

Example usage:
    python3 retrieve_detection_metadata.py -m 'detections.json' -s '2020-10-01' -e '2020-12-01' -b 10

    Explained:
        Retrieve metadata for up to 500 (10 batches of 50) detections (beginning on Oct 1, 2020 and ending on Dec 1, 2020) and store
            as metadata in detections.json file.
'''

# Standard lib packages
import argparse
import datetime
from datetime import date
import heapq
import json
from pathlib import Path

# 3rd party packages
import requests
from tqdm import tqdm

def main(args):

    total_json_list = []
    
    # Format dates for URL
    start_date = f"{args.start_date.strftime('%m')}%2F{args.start_date.strftime('%d')}%2F{args.start_date.strftime('%Y')}"
    end_date = f"{args.end_date.strftime('%m')}%2F{args.end_date.strftime('%d')}%2F{args.end_date.strftime('%Y')}"

    # Save metadata into memory page by page (i.e. batch by batch)
    for i in tqdm(list(range(1, args.max_batch+1))):
        req = f'https://aifororcasdetections.azurewebsites.net/api/detections?Page={i}&SortBy=timestamp&SortOrder=desc&Timeframe=range&DateFrom={start_date}&DateTo={end_date}&Location=all&RecordsPerPage=50'
        r = requests.get(req)
        total_json_list += r.json()

    # Dump metadata json onto disk
    with open(args.metadata_file, 'w') as jf:
        json.dump(total_json_list, jf)


if __name__ == "__main__":

    parser = argparse.ArgumentParser()

    parser.add_argument(
        '-m',
        '--metadata_file',
        type=Path,
        required=True,
        help="Target location to store all retrieved OrcaHello JSON detection metadata."
    )

    parser.add_argument(
        '-s',
        '--start_date',
        type=date.fromisoformat,
        required=False,
        default=date.fromisoformat('2020-10-01'),
        help=f'Start date from which to retrieve OrcaHello detection metadata (inclusive)'
    )

    parser.add_argument(
        '-e',
        '--end_date',
        type=date.fromisoformat,
        required=False,
        default=date.fromisoformat('2020-12-01'),
        help=f'End date through which to retrieve OrcaHello detection metadata (inclusive)'
    )

    parser.add_argument(
        '-b',
        '--max_batch',
        type=int,
        required=False,
        default=10,
        help=f'Maximum number of batches of detections (multiples of 50) about which to retrieve metadata. 10 batches will retreive metadata for at most 500 detections.'
    )

    args = parser.parse_args()
    assert(args.start_date < args.end_date)
    main(args)
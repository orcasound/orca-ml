'''
Purpose:
    Download metadata-specified, annotated dataset as 60sec .wav files and splice into 1sec clips.

Instruction:
    Metadata file must have the following minimum JSON:
        * Following fields must be present.
        * Lists may have more than 1 entry.
        * Objects may have more fields.
        [{
            "audioUri": "https://livemlaudiospecstorage.blob.core.windows.net/audiowavs/rpi_orcasound_lab_2022_12_23_19_16_13_PST.wav",
            "timestamp": "2022-12-24T03:16:13.341389Z", 
            "annotations":
            [{
                    "id": 1,
                    "startTime": 12.2033898305085,
                    "endTime": 13.22033898305087,
                    "confidence": 0.509727999567986
            }], 
            "found": "No", 
        }]

Example usage:
    python3 generate_clip_dataset.py -m 'latest_detections.json' -c 'data/processed/' --top_k 2 --round_name "Era1"

    Explained:
        Retrieve two (or fewer if not available) clips with highest confidence from all detection segments annotated in
            latest_detections.json (metadata file) and store corresponding 1-sec wav files in
            data/processed/[positive|negative]/ with name
            format k<rank>_conf<confidence score of clip>_<original wav detection filename>_<round_name>.wav
'''

# Standard lib packages
import argparse
import heapq
import json
from pathlib import Path

# 3rd party packages
import requests
import torchaudio
from tqdm import tqdm

def generate(args):

    assert(args.top_k >= 0)

    # Prepare data folders
    Path(f"{args.clip_folder}/positive").mkdir(parents=True, exist_ok=True)
    Path(f"{args.clip_folder}/negative").mkdir(parents=True, exist_ok=True)
    Path(f"{args.clip_folder}/unknown").mkdir(parents=True, exist_ok=True)

    # Read metadata of all intended downloads
    detections_metadata = []
    with open(args.metadata_file, 'r') as meta_file:
        detections_metadata = json.load(meta_file)
    
    for segment in tqdm(detections_metadata):
        # Retrieve entire detection audio segment (60sec)
        waveform = None
        sample_rate = None
        with requests.get(segment['audioUri']) as response:
            waveform, sample_rate = torchaudio.load(response.content)

        # Keep all clips within segment if false positive (we know these clips must be false)
        # Keep only top k ranked clips within segment if true positive (we know ONLY that at least one of these clips must be true positive)
        clip_list = []
        top_k_clips = []
        for clip in segment['annotations']:
            clip_list.append((clip['confidence'], clip['id'], clip['startTime'], clip['endTime'],))
        if segment["found"] == "no" or args.top_k == 0:
            top_k_clips = clip_list
        else:
            top_k_clips = heapq.nlargest(args.top_k, clip_list)

        # Classify clips
        classification = "unknown"
        if segment["found"] == "yes":
            classification = "positive"
        elif segment["found"] == "no":
            classification = "negative"

        # Splice out the clips with rank <= k
        # k == 1 assigned to clip with lowest confidence
        # k == n assigned to clip with nth highest confidence
        # Clips rounded down to nearest second (i.e. start time of 0m:23s:998ms translates to clip_start == 23)
        k_ctr = 1
        for clip in top_k_clips:
            clip_start = int(clip[2]*sample_rate)
            clip_end = int(clip[3]*sample_rate)
            clip_waveform = waveform[:, clip_start:clip_end]

            # Save spliced audio to disk as wav
            filepath = Path(args.clip_folder) / classification / Path(f"k{k_ctr}_conf{round(clip[0], 3)}_{Path(segment['audioUri']).name}_{args.round_name}.wav")
            torchaudio.save(filepath, clip_waveform, sample_rate)
            k_ctr += 1

if __name__ == "__main__":

    parser = argparse.ArgumentParser()

    parser.add_argument(
        '-m',
        '--metadata_file',
        type=Path,
        required=True,
        help= '''
            File location of OrcaHello JSON detection metadata for all segments (minutes) and clips (seconds) which user cares to download.
            See this file header for metadata format expectations
        '''
    )

    parser.add_argument(
        '-c',
        '--clip_folder',
        type=Path,
        required=False,
        default=Path.cwd().parent / 'data' / 'processed',
        help=f'Location of positive/, negative/, and unknown/ folders in which to store clips (i.e. one-second wav files spliced from minute-long detection segments)'
    )

    parser.add_argument(
        '-k',
        '--top_k',
        type=int,
        required=False,
        default=60,
        help=f'Retrieve only the max(k, # of detection clips in segment) clips from an OrcaHello minute-long detection segment. k == 60 keeps all (up to 60 seconds) clips'
    )

    parser.add_argument(
        '-r',
        '--round_name',
        type=str,
        required=False,
        default="",
        help=f'String to be appended at end of output 1-sec wav filenames; useful to track which files were created and when'
    )

    args = parser.parse_args()

    generate(args)
'''
Purpose:
    Download metadata-specified, annotated dataset as .wav files and splice into 1sec spectrograms.

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
    python3 generate_spectrogram_dataset.py -m 'latest_detections.json' -e 'data/processed/' --top_k 2 --round_name "Era1"

    Explained:
        Retrieve two (or fewer if not available) examples with highest confidence from all detections annotated in
            latest_detections.json (metadata file) and store corresponding 1-sec wav files in
            data/processed/[positive|negative]/ with name
            format k<rank>_conf<confidence score of example>_<original wav detection filename>_<round_name>.wav
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

def main(args):

    # Prepare data folders
    Path(f"{args.example_folder}/positive").mkdir(parents=True, exist_ok=True)
    Path(f"{args.example_folder}/negative").mkdir(parents=True, exist_ok=True)
    Path(f"{args.example_folder}/unknown").mkdir(parents=True, exist_ok=True)

    # Read metadata of all intended downloads
    detections_metadata = []
    with open(args.metadata_file, 'r') as meta_file:
        detections_metadata = json.load(meta_file)
    
    for detection in tqdm(detections_metadata):
        # Retrieve entire detection audio segment (60sec)
        waveform = None
        sample_rate = None
        with requests.get(detection['audioUri']) as response:
            waveform, sample_rate = torchaudio.load(response.content)

        # Keep all examples within detection if false positive detection (we know these examples must be false)
        # Keep only top k ranked examples within detection otherwise (we know ONLY that at least one of these examples must be true)
        example_list = []
        top_k_examples = []
        for example in detection['annotations']:
            example_list.append((example['confidence'],example['id'],example['startTime'],example['endTime'],))
        if detection["found"] == "no" or args.top_k == 0:
            top_k_examples = example_list
        else:
            top_k_examples = heapq.nlargest(args.top_k, example_list)

        # Classify examples
        classification = "unknown"
        if detection["found"] == "yes":
            classification = "positive"
        elif detection["found"] == "no":
            classification = "negative"

        # Splice out the examples with rank <= k
        # k == 1 assigned to example with lowest confidence
        # k == n assigned to example with nth highest confidence
        k_ctr = 1
        for example in top_k_examples:
            exampleStart = int(example[2]*sample_rate)
            exampleEnd = int(example[3]*sample_rate)
            example_waveform = waveform[:, exampleStart:exampleEnd]

            # Save spliced audio to disk as wav
            filepath = Path(args.example_folder) / classification / Path(f"k{k_ctr}_conf{round(example[0], 3)}_{Path(detection['audioUri']).name}_{args.round_name}.wav")
            torchaudio.save(filepath, example_waveform, sample_rate)
            k_ctr += 1

if __name__ == "__main__":

    parser = argparse.ArgumentParser()

    parser.add_argument(
        '-m',
        '--metadata_file',
        type=Path,
        required=True,
        help= '''
            File location of OrcaHello JSON detection metadata for all detections (minutes) and examples (seconds) which user cares to download.
            See this file header for metadata format expectations
        '''
    )

    parser.add_argument(
        '-e',
        '--example_folder',
        type=Path,
        required=False,
        default=Path.cwd().parent / 'data' / 'processed',
        help=f'Location of positive/, negative/, and unknown/ folders in which to store examples (i.e. one-second wav files spliced from minute-long detections)'
    )

    parser.add_argument(
        '-k',
        '--top_k',
        type=int,
        required=False,
        default=0,
        help=f'Retrieve only the max(k, # of examples in detection) examples from an OrcaHello minute-long detection. k == 0 keeps all examples'
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

    assert(args.top_k >= 0)

    main(args)
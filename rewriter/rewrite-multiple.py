
import glob
import os
import sys
from rewrite import generate_output_files

if __name__ == "__main__":
    if len(sys.argv) < 3:
        raise Exception("Sorry, please supply an input file and output folder")

    script_file = sys.argv[0]
    input_files = glob.glob(sys.argv[1], recursive=True)
    output_root_directory = sys.argv[2]

    for input_file in input_files:
        input_file_name = os.path.splitext(os.path.basename(input_file))[0]
        output_directory = os.path.join(output_root_directory, input_file_name)

        os.makedirs(output_directory, exist_ok=True)
        generate_output_files(script_file, input_file, output_directory)
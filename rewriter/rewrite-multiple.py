
import glob
import os
import sys
import shutil
from rewrite import generate_output_files, write_file

if __name__ == "__main__":
    if len(sys.argv) < 3:
        raise Exception("Sorry, please supply an input file and output folder")

    script_file = sys.argv[0]
    input_files = glob.glob(sys.argv[1], recursive=True)
    output_root_directory = sys.argv[2]

    for input_file in input_files:
        input_file_name = os.path.splitext(os.path.basename(input_file))[0]
        output_directory = os.path.join(output_root_directory, input_file_name)
        
        if os.path.exists(output_directory):
            shutil.rmtree(output_directory)

        try: 
            generate_output_files(script_file, input_file, output_directory)
            #shutil.rmtree(output_directory, ignore_errors=True)
        except Exception as ex: 
            error_file = os.path.join(output_directory, "errors.txt")
            error_text = f"{ex}"
            write_file(error_file, error_text)
            print("Failed to rewrite file %s with error %s" % (input_file, error_text))
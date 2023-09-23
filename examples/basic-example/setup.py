import os 
import shutil

shutil.copyfile('./scripts/index.html', './scripts/example/index.html')

os.system('emcc ./scripts/example/temp.c -s WASM=1 -o ./scripts/example/output.js -s "EXPORTED_FUNCTIONS=[\'_main\']" --js-library ./scripts/library.js')
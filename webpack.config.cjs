const path = require('path');

module.exports = {
  // Point the entry to your subfolder's main file (e.g., index.js)
  entry: './wrapper/main.js',

  // Configure the output
  output: {
    path: path.resolve(__dirname, 'dist'),
    filename: 'bundle.js'
  },

  // ... (other webpack configurations such as loaders, plugins, etc.)
};
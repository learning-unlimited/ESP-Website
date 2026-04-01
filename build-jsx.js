#!/usr/bin/env node

const fs = require('fs');
const path = require('path');
const { exec } = require('child_process');

// JSX files to transform
const jsxFiles = [
  {
    input: 'esp/public/media/scripts/query-builder.jsx',
    output: 'esp/public/media/scripts/query-builder.js'
  },
  {
    input: 'esp/public/media/scripts/program/modules/scheduling_checks.jsx',
    output: 'esp/public/media/scripts/program/modules/scheduling_checks.js'
  }
];

function buildJsx() {
  console.log('Building JSX files...');
  
  jsxFiles.forEach(({ input, output }) => {
    console.log(`Transforming ${input} -> ${output}`);
    
    const command = `npx babel ${input} --out-file ${output} --presets=@babel/preset-react`;
    
    exec(command, (error, stdout, stderr) => {
      if (error) {
        console.error(`Error transforming ${input}:`, error);
        return;
      }
      if (stderr) {
        console.error(`Babel stderr for ${input}:`, stderr);
      }
      console.log(`Successfully transformed ${input}`);
    });
  });
}

function watchMode() {
  console.log('Watching JSX files for changes...');
  
  const chokidar = require('chokidar');
  
  jsxFiles.forEach(({ input, output }) => {
    const watcher = chokidar.watch(input);
    
    watcher.on('change', () => {
      console.log(`File changed: ${input}`);
      const command = `npx babel ${input} --out-file ${output} --presets=@babel/preset-react`;
      
      exec(command, (error, stdout, stderr) => {
        if (error) {
          console.error(`Error transforming ${input}:`, error);
          return;
        }
        console.log(`Successfully transformed ${input}`);
      });
    });
  });
}

// Check if watch mode is enabled
const isWatchMode = process.argv.includes('--watch');

if (isWatchMode) {
  watchMode();
} else {
  buildJsx();
}

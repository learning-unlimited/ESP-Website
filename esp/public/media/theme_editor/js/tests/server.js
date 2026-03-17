/*
 * Simple connect server for phantom.js
 * Adapted from Modernizr
 */

var connect = require('connect')
  , serveStatic = require('serve-static')
  , http = require('http')
  , fs   = require('fs')
  , app = connect()
      .use(serveStatic(__dirname + '/../../'));

http.createServer(app).listen(3000);

fs.writeFileSync(__dirname + '/pid.txt', process.pid, 'utf-8')
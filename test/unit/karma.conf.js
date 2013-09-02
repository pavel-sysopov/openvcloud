// Karma configuration


// base path, that will be used to resolve files and exclude
basePath = '../..';


// list of files / patterns to load in the browser
files = [
  JASMINE,
  JASMINE_ADAPTER,
  '.files/lib/underscore/underscore-1.4.4.min.js',
  '.files/lib/URI.js',
  '.files/lib/angular-1.0.7/angular.js',
  '.files/lib/angular-1.0.7/angular-resource.js',
  '.files/lib/angular-ui/ui-bootstrap-0.4.0.js',
  '.files/lib/angular-1.0.7/angular-mocks.js',
  'test/unit/config.js',
  '.files/js/*.js',
  '.files/js/**/*.js',
  'test/unit/unitAPIStub.js',
  'test/unit/*.js',
  'test/unit/**/*.js'
];


// list of files to exclude
exclude = [
  
];


// test results reporter to use
// possible values: 'dots', 'progress', 'junit'
reporters = ['progress'];


// web server port
port = 9876;


// cli runner port
runnerPort = 9100;


// enable / disable colors in the output (reporters and logs)
colors = true;


// level of logging
// possible values: LOG_DISABLE || LOG_ERROR || LOG_WARN || LOG_INFO || LOG_DEBUG
logLevel = LOG_INFO;


// enable / disable watching file and executing tests whenever any file changes
autoWatch = true;


// Start these browsers, currently available:
// - Chrome
// - ChromeCanary
// - Firefox
// - Opera
// - Safari (only Mac)
// - PhantomJS
// - IE (only Windows)
browsers = ['Chrome'];


// If browser does not capture in given timeout [ms], kill it
captureTimeout = 60000;


// Continuous Integration mode
// if true, it capture browsers, run tests and exit
singleRun = false;


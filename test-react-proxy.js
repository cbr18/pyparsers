// Test script for React image proxy functionality
// This simulates the browser environment for testing

// Mock window.location for testing
global.window = {
  location: {
    hostname: 'localhost'
  }
};

// Mock URL constructor for testing
global.URL = class URL {
  constructor(url) {
    this.hostname = new URL(url).hostname;
  }
};

// Import the image proxy function
const { getProxiedImageUrl, shouldUseProxy } = require('./telegramapp/src/utils/imageProxy.js');

console.log('Testing React Image Proxy Functions');
console.log('==================================');

// Test cases
const testCases = [
  {
    name: 'External HTTPS URL',
    url: 'https://autoimg.cn/example.jpg',
    expected: true
  },
  {
    name: 'External HTTP URL',
    url: 'http://example.com/image.jpg',
    expected: true
  },
  {
    name: 'Relative URL',
    url: '/images/car.jpg',
    expected: false
  },
  {
    name: 'Data URL',
    url: 'data:image/svg+xml;base64,PHN2ZyB3aWR0aD0iMTAwIiBoZWlnaHQ9IjEwMCI+PC9zdmc+',
    expected: false
  },
  {
    name: 'Same domain URL',
    url: 'https://localhost/images/car.jpg',
    expected: false
  },
  {
    name: 'Empty URL',
    url: '',
    expected: false
  },
  {
    name: 'Null URL',
    url: null,
    expected: false
  }
];

console.log('\nTesting shouldUseProxy function:');
testCases.forEach(testCase => {
  const result = shouldUseProxy(testCase.url);
  const status = result === testCase.expected ? '✓' : '✗';
  console.log(`${status} ${testCase.name}: ${result} (expected: ${testCase.expected})`);
});

console.log('\nTesting getProxiedImageUrl function:');
testCases.forEach(testCase => {
  const result = getProxiedImageUrl(testCase.url);
  const isProxied = result && result.startsWith('/proxy-image/');
  const expectedProxied = testCase.expected;
  const status = isProxied === expectedProxied ? '✓' : '✗';
  console.log(`${status} ${testCase.name}:`);
  console.log(`  Input: ${testCase.url}`);
  console.log(`  Output: ${result}`);
  console.log(`  Is proxied: ${isProxied}`);
  console.log('');
});

console.log('Test completed!');

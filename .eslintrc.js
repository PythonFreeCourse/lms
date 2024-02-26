module.exports = {
  "env": {
    "browser": true,
    "node": true
  },
  "ignorePatterns": [
    "/lms/static/prism.js",
    "/lms/static/markdown.js",
  ],
  "globals": {
    "bootstrap": true,
    "Dropzone": true,
    "workbox": true,
  },
  "extends": "eslint:recommended",
  "parserOptions": {
      "ecmaVersion": "latest",
      "sourceType": "module"
  },
  rules: {
    'no-param-reassign': [2, { props: false }],
    'no-console': 'off',
  },
};

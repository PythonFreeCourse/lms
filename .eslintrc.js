module.exports = {
  env: {
    browser: true,
    es2021: true,
  },
  globals: {
    bootstrap: true,
    Dropzone: true,
  },
  extends: [
    'airbnb-base',
  ],
  parserOptions: {
    ecmaVersion: 12,
    sourceType: 'module',
  },
  rules: {
    'no-param-reassign': [2, { props: false }],
  },
};

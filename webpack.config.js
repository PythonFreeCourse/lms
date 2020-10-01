const path = require('path');
const webpack = require('webpack');

const { CleanWebpackPlugin } = require('clean-webpack-plugin');
const HtmlWebpackPlugin = require('html-webpack-plugin');
const autoprefixer = require('autoprefixer');
const precss = require('precss');
const MiniCssExtractPlugin = require('mini-css-extract-plugin');
const TerserPlugin = require('terser-webpack-plugin');

const isProduction = process.argv.indexOf('production') !== -1;

const shared = ['bootstrap', './my.css'];
const pageNames = ['banned', 'exercises', 'login', 'status', 'upload', 'user'];
const pages = pageNames.map(
  (pageName) => new HtmlWebpackPlugin({
    inject: false,
    chunks: [pageName],
    minify: isProduction,
    template: path.join('..', 'templates', `${pageName}.j2`),
    filename: path.join('..', '..', 'templates', 'dist', `${pageName}.html`),
  }),
);

module.exports = {
  context: path.resolve(__dirname, 'lms', 'static'),
  entry: {
    user: { import: [...shared] },
    upload: { import: [...shared, 'dropzone', './my.js'] },
    status: { import: [...shared] },
    banned: { import: [...shared] },
    view: { import: [...shared, './my.js', './prism.js', './comments.js'] },
    view_admin: {
      dependOn: 'view',
      import: [
        ...shared, './my.js', './prism.js', './comments.js',
        './keyboard.js', './grader.js',
      ],
    },
  },

  output: {
    path: path.resolve(__dirname, 'lms', 'static', 'dist'),
    publicPath: '/static/',
    filename: path.join('js', '[name].[chunkhash:8].js'),
    chunkFilename: path.join('static', 'js', '[name].[chunkhash:8].chunk.js'),
  },

  plugins: [
    new webpack.ProgressPlugin(),
    new CleanWebpackPlugin(),
    new HtmlWebpackPlugin({
      inject: false,
      chunks: ['view', 'view_admin'],
      minify: isProduction,
      template: path.join('..', 'templates', 'view.j2'),
      filename: path.join('..', '..', 'templates', 'dist', 'view.html'),
    }),
    ...pages,
    new MiniCssExtractPlugin({ filename: 'main.[chunkhash].css' }),
  ],

  module: {
    rules: [
      {
        test: /.(ttf|otf|eot|svg|woff(2)?)(\?[a-z0-9]+)?$/,
        use: [{
          loader: 'file-loader',
          options: {
            name: '[name].[ext]',
            outputPath: path.resolve(__dirname, 'lms', 'static', 'dist', 'fonts'),
            publicPath: '/static/fonts',
          },
        }],
      },
      {
        test: /\.(js|jsx)$/,
        include: [path.resolve(__dirname, 'lms', 'static')],
        loader: 'babel-loader',
      }, {
        test: /\.scss$/i,
        include: [path.resolve(__dirname, 'node_modules', 'bootstrap', 'scss', 'bootstrap.scss')],

        use: [
          { loader: 'style-loader' },
          { loader: 'css-loader' },
          {
            loader: 'postcss-loader',
            options: {
              postcssOptions: {
                plugins() {
                  return [
                    autoprefixer,
                  ];
                },
              },
            },
          },
          { loader: 'sass-loader' },
        ],
      }, {
        test: /\.css$/i,

        use: [
          { loader: MiniCssExtractPlugin.loader },
          {
            loader: 'css-loader',

            options: {
              importLoaders: 1,
              modules: true,
              sourceMap: true,
            },
          },
          {
            loader: 'postcss-loader',

            options: {
              postcssOptions: {
                plugins() {
                  return [
                    precss,
                    autoprefixer,
                  ];
                },
              },
            },
          },
        ],
      }],
  },

  optimization: {
    minimizer: [new TerserPlugin()],
    // runtimeChunk: 'single',

    splitChunks: {
      cacheGroups: {
        vendors: {
          priority: -10,
          test: /[\\/]node_modules[\\/]/,
        },
      },

      chunks: 'async',
      minChunks: 1,
      minSize: 30000,
      name: 'vendors', // TODO: true?
    },
  },
};

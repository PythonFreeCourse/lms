const path = require('path');
const webpack = require('webpack');
const fs = require('fs');

const { CleanWebpackPlugin } = require('clean-webpack-plugin');
const HtmlWebpackPlugin = require('html-webpack-plugin');
const autoprefixer = require('autoprefixer');
const precss = require('precss');
const MiniCssExtractPlugin = require('mini-css-extract-plugin');
const TerserPlugin = require('terser-webpack-plugin');

const isProduction = process.argv.indexOf('production') !== -1;

const shared = [
  path.resolve(__dirname, 'node_modules', 'bootstrap', 'scss', 'bootstrap.scss'),
  './my.css',
];

function findTemplates(dirPath) {
  const dir = fs.opendirSync(dirPath);
  const filenames = [];
  let currentDir = dir.readSync();
  while (currentDir !== null) {
    if (currentDir.name.endsWith('.j2')) {
      filenames.push(currentDir.name.slice(0, -3));
    }
    currentDir = dir.readSync();
  }
  dir.closeSync();
  return filenames;
}

const templatesDir = path.resolve(__dirname, 'lms', 'templates');
const templates = findTemplates(templatesDir);
const specialTemplates = ['view'];
const autoCompile = templates.filter((x) => !specialTemplates.includes(x));
const pages = autoCompile.map(
  (pageName) => new HtmlWebpackPlugin({
    inject: false,
    chunks: [pageName],
    minify: isProduction,
    template: path.join('..', 'templates', `${pageName}.j2`),
    filename: path.join('..', '..', 'templates', 'dist', `${pageName}.j2`),
  }),
);

const defaultPages = {};
autoCompile.forEach((page) => {
  defaultPages[page] = { import: [...shared] };
});

module.exports = {
  context: path.resolve(__dirname, 'lms', 'static'),
  entry: {
    ...defaultPages,
    upload: { import: [...shared, 'dropzone', './my.js'] },
    view: {
      import: [
        ...shared, './my.js', './prism.css', './prism.js', './comments.js',
      ],
    },
    view_admin: {
      dependOn: 'view',
      import: [
        ...shared, './my.js', './prism.css', './prism.js', './comments.js',
        './keyboard.js', './grader.js',
      ],
    },
  },

  output: {
    path: path.resolve(__dirname, 'lms', 'static', 'dist'),
    publicPath: '/dist/',
    filename: path.join('js', '[name].[chunkhash:8].js'),
    chunkFilename: path.join('js', '[name].[chunkhash:8].chunk.js'),
  },

  plugins: [
    new webpack.ProgressPlugin(),
    new CleanWebpackPlugin(),
    ...pages,
    new HtmlWebpackPlugin({
      inject: false,
      chunks: ['view', 'view_admin'],
      minify: isProduction,
      template: path.join('..', 'templates', 'view.j2'),
      filename: path.join('..', '..', 'templates', 'dist', 'view.j2'),
    }),
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
            publicPath: '/dist/fonts',
          },
        }],
      },
      {
        test: /\.(js|jsx)$/,
        include: [path.resolve(__dirname, 'lms', 'static')],
        loader: 'babel-loader',
      }, {
        test: /\.s[ac]ss$/i,

        use: [
          { loader: 'style-loader' },
          { loader: MiniCssExtractPlugin.loader },
          {
            loader: 'css-loader',
            options: {
              modules: false,
              sourceMap: !isProduction,
            },
          },
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
          {
            loader: 'sass-loader',
            options: {
              sassOptions: {
                sourceMap: !isProduction,
              },
            },
          },
        ],
      }, {
        test: /\.css$/i,

        use: [
          { loader: MiniCssExtractPlugin.loader },
          {
            loader: 'css-loader',

            options: {
              importLoaders: 1,
              sourceMap: true,
              modules: { auto: true },
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
  performance: { hints: false },
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

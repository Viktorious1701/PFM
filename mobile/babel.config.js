module.exports = function (api) {
  api.cache(true);
  return {
    presets: ['babel-preset-expo'],
    // react-native-reanimated v4 moved its Babel plugin here; must stay last.
    plugins: ['react-native-worklets/plugin'],
  };
};

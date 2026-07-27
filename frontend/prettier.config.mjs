export default {
  printWidth: 100,
  semi: true,
  singleQuote: false,
  trailingComma: "all",
  vueIndentScriptAndStyle: false,
  overrides: [
    {
      files: "*.md",
      options: {
        proseWrap: "preserve",
      },
    },
  ],
};

import js from '@eslint/js'
import prettier from 'eslint-config-prettier'
import jsxA11y from 'eslint-plugin-jsx-a11y'
import reactHooks from 'eslint-plugin-react-hooks'
import tseslint from 'typescript-eslint'

export default tseslint.config(
  { ignores: ['dist/', 'src/api/generated/'] },
  js.configs.recommended,
  tseslint.configs.strictTypeChecked,
  reactHooks.configs.flat.recommended,
  jsxA11y.flatConfigs.recommended,
  {
    languageOptions: {
      parserOptions: { projectService: true, tsconfigRootDir: import.meta.dirname },
    },
  },
  { files: ['**/*.js'], extends: [tseslint.configs.disableTypeChecked] },
  prettier,
)

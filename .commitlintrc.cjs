module.exports = {
  extends: ['@commitlint/config-conventional'],
  rules: {
    'header-max-length': [2, 'always', 100],
    'type-enum': [
      2,
      'always',
      [
        'feat',
        'fix',
        'docs',
        'style',
        'refactor',
        'perf',
        'test',
        'chore',
        'ci',
        'experiment'
      ]
    ],
    // 'never' + the 4 disallowed patterns (this repo's own explicit
    // restatement of @commitlint/config-conventional's real upstream
    // default) -- NOT 'always' + an allow-list. An allow-list of
    // ['sentence-case', 'start-case', 'lower-case'] requires the ENTIRE
    // subject to match one of those case classifications, which rejects
    // any embedded acronym (e.g. "PR-controlled", "PR/CI") since a mid-
    // subject capitalized acronym matches none of the three. Verified
    // against this repo's own real commit history: 4 of 6 commits in
    // PR #294 alone failed under the 'always' allow-list form and passed
    // cleanly under this 'never' form, which still rejects genuinely bad
    // casing (Start Case, Sentence case, UPPER CASE).
    'subject-case': [2, 'never', ['sentence-case', 'start-case', 'pascal-case', 'upper-case']],
    'scope-case': [2, 'always', 'kebab-case'],
    'body-leading-blank': [2, 'always'],
    'footer-leading-blank': [1, 'always']
  }
};

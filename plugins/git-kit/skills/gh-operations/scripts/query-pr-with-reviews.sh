#!/usr/bin/env bash
# GraphQL example: fetch a PR's title, state, author, reviews, and latest commit status.
gh api graphql -f query='
  query($owner: String!, $name: String!, $number: Int!) {
    repository(owner: $owner, name: $name) {
      pullRequest(number: $number) {
        title
        state
        author {
          login
        }
        reviews(first: 10) {
          nodes {
            state
            author {
              login
            }
            submittedAt
          }
        }
        commits(last: 1) {
          nodes {
            commit {
              statusCheckRollup {
                state
              }
            }
          }
        }
      }
    }
  }
' -f owner="owner" -f name="repo" -F number=123

`Context mode: review`

I can't write `ship`. The rule allows it only when "the required checks were green and secretlint had passed (or its failure was triaged)". This secretlint failure hasn't been looked at, so fix work may still be needed. For that case the rule says to use `review`: "whenever a PR is open and review or fix work may still be needed. When unsure between `review` and `ship`, choose `review`."

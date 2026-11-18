Context mode: review

Reason: CREATE Step 2 item 5 allows `ship` only when a non-draft PR already exists, and here no PR exists yet. The rule says to use `review` "when the next step opens the PR", and the user's next step starts by opening it, so `review` applies even though merging follows.

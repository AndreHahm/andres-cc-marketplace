# Complete Example: Global Rule

A full worked example of a global (non-path-scoped) rule file, referenced from `references/examples.md`. This is the content of `.claude/rules/use-early-returns.md`.

**Frontmatter:**
```yaml
title: Use Early Returns to Reduce Nesting
impact: MEDIUM
paths:
  - "**/*.ts"
```

# Use Early Returns to Reduce Nesting

Handle error conditions and edge cases at the top of functions using early returns. Deeply nested code increases cognitive load and makes logic harder to follow.

## Incorrect

Guard clauses are buried inside nested conditionals, making the happy path hard to find.

```typescript
function processOrder(order: Order) {
  if (order) {
    if (order.items.length > 0) {
      if (order.status === 'pending') {
        // actual logic buried 3 levels deep
        const total = calculateTotal(order.items)
        return submitOrder(order, total)
      } else {
        throw new Error('Order not pending')
      }
    } else {
      throw new Error('No items')
    }
  } else {
    throw new Error('No order')
  }
}
```

## Correct

Error conditions are handled first with early returns, keeping the happy path at the top level.

```typescript
function processOrder(order: Order) {
  if (!order)
    throw new Error('No order')
  if (order.items.length === 0)
    throw new Error('No items')
  if (order.status !== 'pending')
    throw new Error('Order not pending')

  const total = calculateTotal(order.items)
  return submitOrder(order, total)
}
```

## Reference

- [Flattening Arrow Code](https://blog.codinghorror.com/flattening-arrow-code/)

# Storefront UI Comparison — {{CANDIDATE_NAME}} vs {{BASELINE_NAME}}

**Baseline:** `{{BASELINE_NAME}}` ({{BASELINE_VERSION}}) — treated as the stable storefront UI
**Under test:** `{{CANDIDATE_NAME}}` ({{CANDIDATE_VERSION}})

> Name the projects the way the user named them. Version numbers appear only as a parenthetical,
> never as the subject of a sentence — the reader picked which install is stable, not the version.

## How this was checked

Both installations run on the same machine, same browser, {{same|different}} seed data, and were
compared side by side at **1440×900 (desktop)** and **390×844 (mobile)** across:

{{list the pages and interactive states actually captured}}

Pages were pixel-diffed where the DOM matched, and the two Blade/Tailwind trees were diffed
class-token by class-token against the compiled theme CSS.

**Excluded as intentional feature/config, seed data or environment (not reported below):**
{{one clause per exclusion, each naming the config key, table, count or env value that proves it}}

---

## 1. {{Page/section}} — {{one-line symptom}}

| | |
|---|---|
| **Page/Section** | {{where in the storefront}} |
| **Severity** | **{{High\|Medium\|Low}}** |

**Expected (`{{BASELINE_NAME}}`):** {{what the baseline does}}

**Actual (`{{CANDIDATE_NAME}}`):** {{what the candidate does, concretely — sizes, colours, text}}

**Cause (verified):** {{the file:line, class, config key or generated CSS rule, with the evidence}}

```
{{command output, generated CSS, or emitted URL that demonstrates it}}
```

**Steps to reproduce**
1. {{...}}
2. {{...}}

**Relevant files**
- `{{path/to/file.blade.php:LINE}}`

{{Measured numbers, when a size or spacing changed:}}

| | `{{BASELINE_NAME}}` | `{{CANDIDATE_NAME}}` |
|---|---|---|
| {{property}} | {{value}} | {{value}} |

---

## {{n}}. {{next finding}}

{{same shape}}

---

## Areas checked and found visually equivalent

{{Name them. This is what tells the reader the coverage of the comparison rather than leaving them
to guess, and it is where you state the pages that pixel-diffed to zero.}}

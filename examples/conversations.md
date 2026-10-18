# Synthetic Conversation Examples

All people, identities, messages, and events in this directory are fictional evaluation fixtures. They are not profiles of the repository owner or any real user.

## A Temporary Request

```text
User: Keep today's status update short.
Agent: Provides a short update for that task.
```

Expected memory decision: a temporary instruction scoped to the status update. Do not create "The user dislikes detailed answers."

## An Explicit Lasting Preference

```text
User: For future answers, start with the conclusion. Keep simple questions
short, but include the full steps and validation for complex implementation work.
```

Expected memory decision: add a confirmed conditional rule with a source reference. See [the synthetic guide](USER_SKILL.md).

## A Repeated Pattern

```text
Task A, day 1: Please add a worked example to explain that formula.
Task B, day 3: A concrete example would help me understand the API.
Task C, day 5: Can you walk through one actual-looking input and output?
```

Expected memory decision: a tentative preference for worked examples in explanations. Record all three independent sources and check for explicit contrary instructions. The repetition threshold does not imply a measured probability.

## A Correction

```text
User: I don't want a bullet list for every answer. Use paragraphs unless
we're comparing options or following a sequence of steps.
```

Expected memory decision: immediately apply this scoped structure preference and replace an incompatible active rule. Do not keep both "Always use bullets" and "Default to paragraphs" as equally active rules.

## Material About Someone Else

```text
User: Rewrite this sentence: "My colleague prefers a formal tone."
```

Expected memory decision: no preference about the current user. The sentence is task material, not personal evidence.

## Forgetting

```text
User: Forget the nickname preference I gave you earlier.
```

Expected memory decision: remove the affected content from controlled active and historical stores, record only permitted suppression metadata, and prevent reconstruction from the same old source. Report the actual deletion scope.

## A Later Response

After a confirmed conclusion-first rule is saved, ask the host a new relevant question. Inspect whether the next response starts with the conclusion and provides the right level of detail. This observation is required to establish application; a generated example alone does not prove that a host performed recall.

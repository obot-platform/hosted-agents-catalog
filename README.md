# Hosted agents catalog

The agent templates that ship with Obot. Point an Obot **config source** at this
repository and it registers every harness and template in it.

The images these run on are built in
[hosted-agents-images](https://github.com/obot-platform/hosted-agents-images).

| Template | Harness | What it is |
|---|---|---|
| Claude Code | Claude Code | A coding agent with a terminal. The user supplies a repository. |
| Codex | Codex CLI | The same, on OpenAI's Codex CLI. |
| ADK Chatbot | ADK | A conversational agent with a web UI, published on a port. |

## Layout

Obot discovers definitions **by filename, anywhere in the tree**: every
`harness.yaml` is a harness and every `agent.yaml` is a template. One directory
per agent:

```
claude-code/
  harness.yaml   the image, and whether it needs a TTY
  agent.yaml     the template: what it may use, and what the user is asked
```

A template names its harness by that harness's path in this repository
(`harnessID: claude-code/harness.yaml`). Obot rewrites it to the stored ID on
sync, because a repository cannot know the IDs an installation will generate.

## Conventions

* **A harness is a runtime, not an agent.** Where an agent is a program rather
  than a CLI, the harness supplies the runtime and the template points at the
  repository holding the code, so one harness serves many agents.
* **`interactive` and `terminal` go together.** A template offering a terminal
  must sit on an interactive harness, or there is no console to attach to. CI
  rejects the mismatch.
* **`port` and `terminal` are administrator decisions.** They describe what the
  image does, which the user instantiating it has no way to know.
* **Name what an agent needs.** `modelProviders` restricts a template to models
  from those providers and is what lets Obot report the agent unavailable, by
  name, where the provider is not configured.
* **Reference other things portably.** MCP servers and skills are named
  `<source>::<key>` rather than by ID, which differs per installation.
* **Never commit a secret.** An `env` entry marked `sensitive` must carry no
  value; CI rejects it, as does Obot at sync.

## Releasing

There is no release tag here: an installation syncs `main`, so merging is
releasing. That is why CI validates every pull request the way Obot validates a
sync -- a template that would fail to sync fails the build instead.

Image tags are updated by a pull request the images repository opens when it
publishes a release.
